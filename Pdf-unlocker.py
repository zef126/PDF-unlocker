import sys
import os
import json
import warnings
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel, QFileDialog, QPushButton,
                             QMessageBox, QDialog, QLineEdit, QCheckBox, QDialogButtonBox,
                             QComboBox, QHBoxLayout)
from PyQt6.QtCore import Qt
import pikepdf

PASSWORDS_FILE = os.path.join(os.path.expanduser("~"), ".pdf_unlocker_passwords.json")

def load_passwords():
    if os.path.exists(PASSWORDS_FILE):
        try:
            with open(PASSWORDS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_passwords(passwords):
    try:
        with open(PASSWORDS_FILE, "w") as f:
            json.dump(passwords, f)
    except Exception:
        pass

def abbreviate(pw):
    if len(pw) < 4:
        return pw
    return pw[:3] + "…" + pw[-1]

class PasswordDialog(QDialog):
    def __init__(self, stored_passwords, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mot de passe")
        self.setModal(True)
        self.resize(400, 130)
        self.stored_passwords = stored_passwords
        main_layout = QVBoxLayout(self)
        hlayout = QHBoxLayout()
        self.combo = QComboBox(self)
        self.combo.setEditable(False)
        self.combo.addItem("")
        for pw in self.stored_passwords:
            self.combo.addItem(abbreviate(pw), pw)
        self.combo.currentIndexChanged.connect(self.combo_changed)
        hlayout.addWidget(self.combo)
        self.del_button = QPushButton("🗑", self)
        self.del_button.setFixedWidth(30)
        self.del_button.clicked.connect(self.delete_current)
        hlayout.addWidget(self.del_button)
        main_layout.addLayout(hlayout)
        self.pw_edit = QLineEdit(self)
        self.pw_edit.setEchoMode(QLineEdit.EchoMode.Password)
        main_layout.addWidget(self.pw_edit)
        hlayout2 = QHBoxLayout()
        self.show_checkbox = QCheckBox("Show Password", self)
        self.show_checkbox.stateChanged.connect(self.toggle_password_visibility)
        hlayout2.addWidget(self.show_checkbox)
        self.memo_checkbox = QCheckBox("Memorize Password", self)
        hlayout2.addWidget(self.memo_checkbox)
        main_layout.addLayout(hlayout2)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    def combo_changed(self, index):
        data = self.combo.itemData(index)
        if data:
            self.pw_edit.setText(data)

    def delete_current(self):
        index = self.combo.currentIndex()
        if index <= 0:
            return
        pw = self.combo.itemData(index)
        del self.stored_passwords[self.stored_passwords.index(pw)]
        self.combo.removeItem(index)
        save_passwords(self.stored_passwords)

    def toggle_password_visibility(self, state):
        if state == Qt.CheckState.Checked.value:
            self.pw_edit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.pw_edit.setEchoMode(QLineEdit.EchoMode.Password)

    def get_password(self):
        return self.pw_edit.text(), self.memo_checkbox.isChecked()

class PDFUnlockerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Déverrouilleur de PDF")
        self.setGeometry(100, 100, 500, 220)
        layout = QVBoxLayout()
        self.label = QLabel("Glissez-déposez ici les fichiers PDF à déverrouiller", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        self.select_button = QPushButton("Sélectionner des fichiers PDF", self)
        self.select_button.clicked.connect(self.select_files)
        layout.addWidget(self.select_button)
        self.setLayout(layout)
        self.setAcceptDrops(True)
        warnings.filterwarnings("ignore", message="A password was provided, but no password was needed to open this PDF.")
        self.candidate_passwords = load_passwords()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        file_paths = [url.toLocalFile() for url in event.mimeData().urls()]
        self.process_pdfs(file_paths)
        self.label.setText("Glissez-déposez ici les fichiers PDF à déverrouiller")

    def select_files(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Sélectionner des fichiers PDF", "", "Fichiers PDF (*.pdf)")
        if file_paths:
            self.process_pdfs(file_paths)

    def process_pdfs(self, file_paths):
        unlocked_files = []
        wrong_password_files = []
        no_password_files = []
        for filepath in file_paths:
            try:
                with pikepdf.open(filepath, allow_overwriting_input=True) as pdf:
                    no_password_files.append(filepath)
                    continue
            except pikepdf.PasswordError:
                pass
            except Exception as e:
                QMessageBox.critical(self, "Erreur", f"Erreur avec {filepath}:\n{e}")
                continue
            tested = False
            for pw in self.candidate_passwords:
                try:
                    with pikepdf.open(filepath, password=pw, allow_overwriting_input=True) as pdf:
                        with pikepdf.open(filepath, password=pw, allow_overwriting_input=True) as pdf2:
                            pdf2.save(filepath)
                    unlocked_files.append(filepath)
                    tested = True
                    break
                except pikepdf.PasswordError:
                    continue
                except Exception as e:
                    QMessageBox.critical(self, "Erreur", f"Erreur lors de l'enregistrement de {filepath}:\n{e}")
                    tested = True
                    break
            if tested:
                if filepath not in unlocked_files:
                    wrong_password_files.append(filepath)
                continue
            while True:
                dlg = PasswordDialog(self.candidate_passwords, self)
                if dlg.exec() != QDialog.DialogCode.Accepted:
                    wrong_password_files.append(filepath)
                    break
                new_pw, memorize = dlg.get_password()
                try:
                    with pikepdf.open(filepath, password=new_pw, allow_overwriting_input=True) as pdf:
                        pdf.save(filepath)
                    unlocked_files.append(filepath)
                    if new_pw not in self.candidate_passwords:
                        self.candidate_passwords.append(new_pw)
                        if memorize:
                            save_passwords(self.candidate_passwords)
                    break
                except pikepdf.PasswordError:
                    continue_choice = QMessageBox.question(self, "Mot de passe incorrect",
                        f"Le mot de passe entré est incorrect pour {filepath}.\nVoulez-vous réessayer ?",
                        QMessageBox.StandardButton.Retry | QMessageBox.StandardButton.Cancel)
                    if continue_choice == QMessageBox.StandardButton.Cancel:
                        wrong_password_files.append(filepath)
                        break
                except Exception as e:
                    QMessageBox.critical(self, "Erreur", f"Erreur lors de l'enregistrement de {filepath}:\n{e}")
                    break
        self.show_results(unlocked_files, wrong_password_files, no_password_files)

    def show_results(self, unlocked_files, wrong_password_files, no_password_files):
        message = ""
        if unlocked_files:
            message += "Fichiers déverrouillés:\n" + "\n".join(unlocked_files) + "\n\n"
        if wrong_password_files:
            message += "Mot de passe incorrect pour:\n" + "\n".join(wrong_password_files) + "\n\n"
        if no_password_files:
            message += "Pas de mot de passe pour:\n" + "\n".join(no_password_files)
        QMessageBox.information(self, "Résultats", message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PDFUnlockerApp()
    window.show()
    sys.exit(app.exec())
