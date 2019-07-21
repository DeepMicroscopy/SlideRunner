import torch
from torch import nn
from torch import Tensor
import torch.nn.functional as F
from typing import Callable, Collection, Union, List, Optional, Any
from torchvision import models
import re
import numpy as np


ModuleList = Collection[nn.Module]
LayerFunc = Callable[[nn.Module],None]


def pil2tensor(image:Union[np.ndarray,np.ndarray],dtype:np.dtype)->Tensor:
    "Convert PIL style `image` array to torch style image tensor."
    a = np.asarray(image)
    if a.ndim==2 : a = np.expand_dims(a,2)
    a = np.transpose(a, (1, 0, 2))
    a = np.transpose(a, (2, 1, 0))
    return torch.from_numpy(a.astype(dtype, copy=False) )


def ifnone(a:Any,b:Any)->Any:
    "`a` if `a` is not None, otherwise `b`."
    return b if a is None else a


def conv2d(ni: int, nf: int, ks: int = 3, stride: int = 1, padding: int = None, bias=False,
           init: LayerFunc = nn.init.kaiming_normal_) -> nn.Conv2d:
    "Create and initialize `nn.Conv2d` layer. `padding` defaults to `ks//2`."
    if padding is None: padding = ks // 2
    return init_default(nn.Conv2d(ni, nf, kernel_size=ks, stride=stride, padding=padding, bias=bias), init)


def init_default(m: nn.Module, func: LayerFunc = nn.init.kaiming_normal_) -> None:
    "Initialize `m` weights with `func` and set `bias` to 0."
    if func:
        if hasattr(m, 'weight'): func(m.weight)
        if hasattr(m, 'bias') and hasattr(m.bias, 'data'): m.bias.data.fill_(0.)
    return m


def in_channels(m: nn.Module) -> List[int]:
    "Return the shape of the first weight layer in `m`."
    for l in flatten_model(m):
        if hasattr(l, 'weight'): return l.weight.shape[1]
    raise Exception('No weight layer')


def children_and_parameters(m: nn.Module):
    "Return the children of `m` and its direct parameters not registered in modules."
    children = list(m.children())
    children_p = sum([[id(p) for p in c.parameters()] for c in m.children()], [])
    for p in m.parameters():
        if id(p) not in children_p: children.append(ParameterModule(p))
    return children


class ParameterModule(nn.Module):
    "Register a lone parameter `p` in a module."

    def __init__(self, p: nn.Parameter):
        super().__init__()
        self.val = p

    def forward(self, x): return x


def num_children(m: nn.Module) -> int:
    "Get number of children modules in `m`."
    return len(children(m))


def children(m: nn.Module) -> ModuleList:
    "Get children of `m`."
    return list(m.children())


flatten_model = lambda m: sum(map(flatten_model, children_and_parameters(m)), []) if num_children(m) else [m]


# By default split models between first and second layer
def _default_split(m:nn.Module): return (m[1],)
# Split a resnet style model
def _resnet_split(m:nn.Module): return (m[0][6],m[1])
# Split squeezenet model on maxpool layers
def _squeezenet_split(m:nn.Module): return (m[0][0][5], m[0][0][8], m[1])
def _densenet_split(m:nn.Module): return (m[0][0][7],m[1])
def _vgg_split(m:nn.Module): return (m[0][0][22],m[1])
def _alexnet_split(m:nn.Module): return (m[0][0][6],m[1])

_default_meta    = {'cut':None, 'split':_default_split}
_resnet_meta     = {'cut':-2, 'split':_resnet_split }
_squeezenet_meta = {'cut':-1, 'split': _squeezenet_split}
_densenet_meta   = {'cut':-1, 'split':_densenet_split}
_vgg_meta        = {'cut':-1, 'split':_vgg_split}
_alexnet_meta    = {'cut':-1, 'split':_alexnet_split}

model_meta = {
    models.resnet18 :{**_resnet_meta}, models.resnet34: {**_resnet_meta},
    models.resnet50 :{**_resnet_meta}, models.resnet101:{**_resnet_meta},
    models.resnet152:{**_resnet_meta},

    models.squeezenet1_0:{**_squeezenet_meta},
    models.squeezenet1_1:{**_squeezenet_meta},

    models.densenet121:{**_densenet_meta}, models.densenet169:{**_densenet_meta},
    models.densenet201:{**_densenet_meta}, models.densenet161:{**_densenet_meta},
    models.vgg16_bn:{**_vgg_meta}, models.vgg19_bn:{**_vgg_meta},
    models.alexnet:{**_alexnet_meta}}

def cnn_config(arch):
    "Get the metadata associated with `arch`."
    torch.backends.cudnn.benchmark = True
    return model_meta.get(arch, _default_meta)

def is_pool_type(l:Callable): return re.search(r'Pool[123]d$', l.__class__.__name__)

def has_pool_type(m):
    if is_pool_type(m): return True
    for l in m.children(): return has_pool_type(l)
    return False

def create_body(arch:Callable, pretrained:bool=True, cut:Optional[Union[int, Callable]]=None):
    "Cut off the body of a typically pretrained `model` at `cut` (int) or cut the model as specified by `cut(model)` (function)."
    model = arch(pretrained)
    cut = ifnone(cut, cnn_config(arch)['cut'])
    if cut is None:
        ll = list(enumerate(model.children()))
        cut = next(i for i,o in reversed(ll) if has_pool_type(o))
    if   isinstance(cut, int):      return nn.Sequential(*list(model.children())[:cut])
    elif isinstance(cut, Callable): return cut(model)
    else:                           raise NamedError("cut must be either integer or a function")