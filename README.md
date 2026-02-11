# Grocery Store Management System

This project is a Grocery Store Management System developed using Flask and SQLite. It provides a virtual platform for managing grocery store operations, including user registration, product browsing, cart management, and admin insights.

## Features

- User Registration and Login
- Browse Products by Categories
- Add and Remove Products from Cart
- Search by Products, Categoeries, Price
- Checkout and Purchase History
- Admin Dashboard for Product and Section Management
- Insights for Store Performance Analysis

## Prerequisites

- Python 3.7 or higher is installed.
- Flask and required packages are installed.

## Installation

1.  Install dependencies:
   
Ensure you have the following packages installed:

```python
import sqlite3, os, uuid
from flask import Flask, render_template, request, session, redirect, url_for, g
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np

2. Sqlite database has pre existed tables no need to create seperatly.

3 Run the application:
  using python main.py
  
  admin login credentials:
  username: navjot
  password: password


## Usage

- Users can register and log in to their accounts.
- Browse products by categories, add products to the cart, and proceed to checkout.
- Users can Search by cateogery, product, and price.
- View purchase history and manage the cart.
- Admin can log in using their credentials.
- Admin can manage products and sections in the admin dashboard.
- View insights about most sold products, low quantity products, and registered users count.

## Technologies Used

- Flask: Web framework for building the application.
- Jinja: It is a web template engine for the Python programming language.
- SQLite: Database management system for data storage.
- HTML/CSS: Front-end for user interface.
- Bootstrap: CSS framework for styling.
- Matplotlib: Used for generating insights graphs.
- Replit: As IDE