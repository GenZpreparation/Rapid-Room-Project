# 🏠 Roomify — Student & Room Rental Platform

A full-stack room rental and property management platform designed to streamline accommodation discovery for students and property management for landlords. Built with Django, Django Channels (WebSockets), and PostgreSQL, deployed on Vercel.

[![Live Demo](https://img.shields.io/badge/Demo-Live%20Website-brightgreen?style=for-the-badge&logo=vercel)](https://rapid-room-project-tau.vercel.app)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2-092E20?style=for-the-badge&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon%20DB-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://neon.tech/)
[![WebSockets](https://img.shields.io/badge/WebSockets-Django%20Channels-orange?style=for-the-badge&logo=socketdotio&logoColor=white)](https://channels.readthedocs.io/)

---

## 🌐 Live Demo

- **Application URL:** [https://rapid-room-project-tau.vercel.app](https://rapid-room-project-tau.vercel.app)
- **Repository:** [https://github.com/GenZpreparation/Rapid-Room-Project](https://github.com/GenZpreparation/Rapid-Room-Project)

---

## ✨ Features

### 👤 Role-Based Portals

#### 🏢 Property Owners (Landlords)
- **Property Listings:** Create, edit, and delete room listings with photo galleries, amenities, address, area, and pricing.
- **Booking Management:** Review incoming booking requests from students with accept/reject actions.
- **Tenancy Management:** Assign tenants to rooms, track ongoing tenancies, and end leases.
- **Rent Tracking:** Manage rent schedules and record payment status.
- **Maintenance Operations:** Review student maintenance tickets with photos, update status (*Submitted*, *In Progress*, *Completed*), and communicate in dedicated threads.

#### 🎓 Students & Tenants
- **Discovery & Search:** Browse available rooms, filter by room type (*Private*, *Shared*, *Apartment*), location, and rent.
- **Room Booking:** Send booking requests directly to landlords with personalized messages.
- **Saved Listings:** Save favorite properties for quick access.
- **Rent Payment Portal:** Integrated mock payment portal supporting card and UPI simulations with instant status update.
- **Maintenance Requests:** Submit issue tickets with photo attachments and priority levels (*Low*, *Medium*, *High*).
- **Ratings & Reviews:** Rate and review rented properties with feedback.

### ⚡ Real-Time Capabilities (WebSockets)
- **Direct Messaging:** Real-time chat between students and landlords powered by Django Channels & ASGI.
- **Live Notifications:** Real-time notifications for incoming bookings, chat messages, and maintenance status updates.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | Django 5.2 (ASGI with Daphne) |
| **Real-time / WebSockets** | Django Channels 4.3, ASGI |
| **Database** | PostgreSQL (Neon Serverless PostgreSQL) |
| **Frontend** | Django Templates, HTML5, CSS3, Modern Responsive UI, JavaScript |
| **File / Media Storage** | Pillow, Cloud Storage (S3 / Supabase compatible) |
| **Hosting & Deployment** | Vercel Serverless Functions + Neon Cloud DB |

---

## 📁 Project Structure

```text
Rapid-Room-Project/
├── homepage/                 # Core application
│   ├── consumers.py          # WebSocket consumers (Chat & Notifications)
│   ├── models.py             # Database models (User, Post, Tenancy, Booking, etc.)
│   ├── routing.py            # WebSocket URL routing
│   ├── urls.py               # HTTP application routes
│   └── views.py              # Application views & controllers
├── SomeNew/                  # Django project configuration
│   ├── asgi.py               # ASGI entrypoint for WebSockets & HTTP
│   ├── settings.py           # Project settings & environment configuration
│   ├── urls.py               # Main URL dispatcher
│   └── wsgi.py               # WSGI fallback entrypoint
├── templates/                # HTML templates (Dashboards, Chat, Auth, Details)
├── static/                   # Static assets (CSS, JS, Icons)
├── media/                    # Media uploads directory
├── .env.example              # Environment variables template
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
└── vercel.json               # Vercel serverless configuration
```

---

## 🚀 Getting Started

Follow these steps to set up and run the project locally.

### 1. Prerequisites
- **Python 3.10+**
- **Git**
- **PostgreSQL** database (Local instance or cloud database via [Neon](https://neon.tech))

### 2. Clone the Repository
```bash
git clone https://github.com/GenZpreparation/Rapid-Room-Project.git
cd Rapid-Room-Project
```

### 3. Create & Activate Virtual Environment

**On Windows:**
```bash
python -m venv env
env\Scripts\activate
```

**On macOS/Linux:**
```bash
python3 -m venv env
source env/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Setup Environment Variables
Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Configure the following variables in `.env`:
```env
SECRET_KEY=your_django_secret_key_here
DEBUG=True

# Database Configuration (Neon or Local PostgreSQL)
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=your_database_host
DB_PORT=5432
DB_SSLMODE=require
```

### 6. Apply Database Migrations
```bash
python manage.py migrate
```

### 7. Run the Development Server
```bash
python manage.py runserver
```

Open your browser and navigate to:
```
http://127.0.0.1:8000/
```

---

## 🔑 Environment Variables Reference

| Variable | Description | Required | Default |
|---|---|:---:|:---:|
| `SECRET_KEY` | Django secret key for cryptographic signing | Yes | — |
| `DEBUG` | Toggle debug mode (`True` for local, `False` for production) | Yes | `False` |
| `DB_NAME` | PostgreSQL database name | Yes | — |
| `DB_USER` | PostgreSQL user name | Yes | — |
| `DB_PASSWORD` | PostgreSQL user password | Yes | — |
| `DB_HOST` | Database host (e.g., Neon pooled endpoint) | Yes | — |
| `DB_PORT` | Database port | Yes | `5432` |
| `DB_SSLMODE` | SSL connection mode (`require` recommended for cloud DB) | No | `require` |
| `EXTRA_ALLOWED_HOSTS` | Comma-separated list of custom domains | No | — |
| `REDIS_URL` | Redis URL for multi-instance WebSocket channel layer | No | — |
| `AWS_STORAGE_BUCKET_NAME` | Cloud storage bucket for persistent media uploads | No | — |

---

## ☁️ Deployment

The project is configured for serverless deployment on **Vercel** with ASGI support (`vercel.json`) and **Neon PostgreSQL**.

1. Connect your repository to **Vercel**.
2. Configure all environment variables listed above in **Project Settings > Environment Variables**.
3. Deploy the application. Static files and ASGI serverless endpoints are managed automatically.

---

## 📄 License

This project is licensed under the MIT License.
