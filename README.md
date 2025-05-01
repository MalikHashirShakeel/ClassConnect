# ClassConnect

## 📚 Description
ClassConnect is a full-featured Django-based web application designed for virtual classroom management. It allows teachers to create classrooms, post assignments and announcements, and enables students to join classes, submit assignments, and engage in discussions. The frontend is styled using Tailwind CSS for a modern and responsive UI.

---

## 🚀 Features
- 🔐 User Authentication (Sign Up, Login, Logout)
- 🏫 Create and Join Classrooms
- 📢 Post Announcements and Assignments
- 🗂️ Submit Assignments
- 💬 Comment on Posts and Submissions
- 🎨 Tailwind CSS Integration for UI Styling

---

## 🛠️ Getting Started
Follow these steps to set up and run the project locally.

### ✅ Prerequisites
- Python 3.10+
- Git
- Node.js and npm (for Tailwind CSS)
- MySQL (or compatible database)

---

## 🧾 Directory Structure Overview
```
ClassConnect/
├── classroom_web_app/       # Main Django project folder (contains manage.py)
├── .gitignore           # Additional resources
├── README.md                # This file
├── venv/                    # Virtual environment (after setup)
```

---

## 🔧 Setup Instructions

### 1. 📥 Clone the Repository
```bash
git clone https://github.com/MalikHashirShakeel/ClassConnect.git
cd ClassConnect
```

### 2. 🧪 Set Up Virtual Environment
Make sure Python is installed.

- **Windows**
```bash
python -m venv venv
venv\Scripts\activate
```

- **macOS/Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 📦 Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 4. 📝 Set Up Environment Variables
1. Copy the example environment file:
```bash
cp .env.example .env   # Use `copy .env.example .env` on Windows
```
2. Fill in your own credentials for database, email, and superuser.

---

### 5. 🛠️ Apply Database Migrations
```bash
cd classroom_web_app
python manage.py migrate
```

### 6. 📐 Build Tailwind CSS
Tailwind requires a separate process to watch and compile CSS.

#### Open **Terminal 1**:
```bash
# Activate virtual environment
cd ClassConnect
venv\Scripts\activate   # or `source venv/bin/activate` on macOS/Linux
cd classroom_web_app
python manage.py tailwind start
```
This watches for Tailwind CSS changes and updates output in real time.

#### Open **Terminal 2**:
```bash
# Activate virtual environment again
cd ClassConnect
venv\Scripts\activate   # or `source venv/bin/activate`
cd classroom_web_app
python manage.py runserver
```

Now open your browser and go to:
[http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 🧠 Tips
- If Tailwind styles don’t apply, make sure `tailwind.config.js` and static setup is correct.
- Keep both terminals open for real-time Tailwind and Django updates.
- Use `.env.example` as a reference for required environment variables.
- Run `python manage.py createsuperuser` if you prefer manual admin setup.

---

## 🤝 Contributing
Fork this repo, make your changes, and submit a pull request. All contributions are welcome!

---

## 📄 License
Licensed under the **MIT License**.

---

> Created with ❤️ by Malik Hashir Shakeel

