# InventoryPro

This Django application offers a solution for managing business operations with an emphasis on user experience and modern web technologies. It integrates Bootstrap for front-end design and employs Ajax for dynamic sales creation. The application features models for user profiles, vendors, customers, and transactions, including billing, invoicing, and inventory management.

## Features
- **User-Friendly Interface**
- **Authentication and Authorization**
- **Inventory Management**: Keep track of stock levels, manage products, and monitor inventory changes.
- **Sales Management**: Record and manage sales transactions, generate sales reports, and analyze sales data.
- **Customer Management**: Maintain customer information, track customer interactions, and manage customer relationships.
- **Supplier Management**: Manage supplier information, track orders, and maintain supplier relationships.
- **Reporting**: Generate various reports for inventory, sales, customers, and suppliers.
- **Multi-Warehouse Support**: Manage inventory across multiple warehouses or locations.
- **Vietnamese Currency (VND)**: All financial transactions are handled in Vietnamese Dong.

## Screenshots
(Add screenshots of your application here)

## Installation

Follow these steps to install the necessary dependencies and set up the application:


#### On Linux

1. **Set Up the Virtual Environment**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2. **Install Dependencies**

    ```bash
    pip install -r requirements.txt
    ```

3. **Apply Migrations and Run the Server**

    ```bash
    python manage.py migrate
    python manage.py runserver
    ```

#### On Windows

1. **Set Up the Virtual Environment**

    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```

2. **Install Dependencies**

    ```bash
    pip install -r requirements.txt
    ```

3. **Apply Migrations and Run the Server**

    ```bash
    python manage.py migrate
    python manage.py runserver
    ```

## Pushing to GitHub

To push this project to GitHub, follow these steps:

1. **Initialize Git Repository** (if not already done)
   ```bash
   git init
   ```

2. **Add Remote Repository**
   ```bash
   git remote add origin https://github.com/SagitaKDX/Inventory-Pro.git
   ```

3. **Add Files to Staging**
   ```bash
   git add .
   ```

4. **Commit Changes**
   ```bash
   git commit -m "Initial commit with VND currency support"
   ```

5. **Push to GitHub**
   ```bash
   git push -u origin main
   ```

## Technologies Used
- Django
- Bootstrap
- JavaScript/Ajax
- SQLite (default database, can be configured for other DB engines)

## License
This project is licensed under the MIT License - see the LICENSE file for details.

