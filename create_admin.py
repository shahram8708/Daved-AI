from app import create_app, db
from app.models import User

app = create_app()
with app.app_context():
    username = "Daved AI"
    email = "admin@davedai.com"
    password = "DavedAI8708@"  

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        print(f"User '{username}' already exists.")
    else:
        
        admin_user = User(
            username=username,
            email=email,
            is_admin=True
        )
        admin_user.set_password(password)
        db.session.add(admin_user)
        db.session.commit()
        print(f"Admin user '{username}' created successfully.")
