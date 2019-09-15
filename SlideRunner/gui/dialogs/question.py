from PyQt5.QtWidgets import QMessageBox, QAbstractButton

def YesNoAbortDialog(title:str='Question', text:str='Answer?', textYes:str='Yes', textNo:str='No', textAbort:str=None):

    box = QMessageBox()
    box.setIcon(QMessageBox.Question)
    box.setWindowTitle(title)
    box.setText(text)

    box.setStandardButtons(QMessageBox.Yes|QMessageBox.No)
    if (textAbort is not None):
        box.setStandardButtons(QMessageBox.Yes|QMessageBox.No|QMessageBox.Abort)
        abortBtn = box.button(QMessageBox.Abort)
        abortBtn.setText(textAbort)
    else:
        abortBtn=None
        
    buttonY = box.button(QMessageBox.Yes)
    buttonY.setText(textYes)
    buttonN = box.button(QMessageBox.No)
    buttonN.setText(textNo)
    box.exec_()

    if (box.clickedButton()==buttonY):
        return QMessageBox.Yes
    elif (box.clickedButton()==buttonN):
        return QMessageBox.No
    elif (box.clickedButton()==abortBtn):
        return QMessageBox.Abort

    return None
