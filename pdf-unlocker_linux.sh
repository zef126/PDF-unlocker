#!/bin/bash
# Vérifie si l'environnement existe
if [ ! -d "pdf-unlock-env-linux" ]; then
    echo "Création de l'environnement virtuel..."
    python3 -m venv pdf-unlock-env-linux
    echo "Activation de l'environnement..."
    source pdf-unlock-env-linux/bin/activate
    echo "Installation des dépendances..."
    pip install --upgrade pip
    pip install -r requirements.txt
else
    source pdf-unlock-env-linux/bin/activate
fi

echo "Lancement du programme..."
python Pdf-unlocker.py
