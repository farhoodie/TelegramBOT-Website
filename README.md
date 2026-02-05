**🐶 DoggoBot — Setup & Run Guide**

**!! Important Note !! These files must be together for everything to work correctly!**

This project is a Telegram moderation bot dashboard built with Python (Flask) and a static HTML/CSS frontend.

📁 Project Structure (important)

Make sure your folder looks something like this:

DoggoBot/
│
├── app.py                # main Flask server file
├── requirements.txt
│
├── index.html
├── login.html
├── register.html
├── admin.html
├── styles.css
│
└── static / templates    # (if you later organize files properly)

⚠️ If your main Python file is not called app.py, replace app.py in the commands below with the correct filename.

🧰 Requirements
1️⃣ Install Python (if not installed)

Windows & macOS: https://www.python.org/downloads/

During installation on Windows, ✅ check “Add Python to PATH”

Verify installation:
**Bash**
python --version
**on mac**
python3 --version

📦 Required Python Libraries

These are listed in requirements.txt:
flask
flask-bcrypt
flask-cors

🚀 How to Run the Project (ALL AT ONCE)
🔹 Step 1: Open a terminal in the project folder
Windows

Command Prompt or PowerShell

Go to the project folder:
cd path\to\DoggoBot

macOS
Open Terminal

cd path/to/DoggoBot

🔹 Step 2: (Optional but recommended) Create a virtual environment
Windows

python -m venv venv
venv\Scripts\activate

Mac
python3 -m venv venv
source venv/bin/activate

🔹 Step 3: Install dependencies
Windows

pip install -r requirements.txt

macOS

pip3 install -r requirements.txt

🔹 Step 4: Run the Flask server
Windows
python app.py
macOS
python3 app.py

If everything is correct, you’ll see something like:

Running on http://127.0.0.1:5000/
🌐 Accessing the Website

Open your browser and go to:

http://127.0.0.1:5000/

Pages available:

/ → Home page

/login → Login page

/register → Register page

/admin → Admin dashboard (demo)

🧠 Notes

The HTML pages are demo UI unless connected to backend routes.

Authentication logic must be handled in Flask.

Admin panel actions are placeholders until linked to the Telegram bot API.

This project is suitable for IB Computer Science IA (Criterion C & D especially).

🛑 Common Errors & Fixes

ModuleNotFoundError: flask

pip install flask

Port already in use

CTRL + C

Then rerun the server.
