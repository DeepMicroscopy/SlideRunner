from PyQt6.QtWidgets import QMessageBox, QAbstractButton

def YesNoAbortDialog(title:str='Question', text:str='Answer?', textYes:str='Yes', textNo:str='No', textAbort:str=None):

    box = QMessageBox()
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(title)
    box.setText(text)

    box.setStandardButtons(QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)
    if (textAbort is not None):
        box.setStandardButtons(QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No|QMessageBox.StandardButton.Abort)
        abortBtn = box.button(QMessageBox.StandardButton.Abort)
        abortBtn.setText(textAbort)
    else:
        abortBtn=None
        
    buttonY = box.button(QMessageBox.StandardButton.Yes)
    buttonY.setText(textYes)
    buttonN = box.button(QMessageBox.StandardButton.No)
    buttonN.setText(textNo)
    box.exec()

    if (box.clickedButton()==buttonY):
        return QMessageBox.StandardButton.Yes
    elif (box.clickedButton()==buttonN):
        return QMessageBox.StandardButton.No
    elif (box.clickedButton()==abortBtn):
        return QMessageBox.StandardButton.Abort

    return None
