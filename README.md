# **LogisTech: Automated Warehouse System**

## **📌 Overview**

LogisTech is a backend simulation for a high-volume fulfillment center. It serves as a centralized orchestration system that manages inventory storage, truck loading, and shipment tracking using a persistent SQL database.

The system handles real-world constraints like "Shipping Air" (wasting space) and complex loading optimizations using efficient algorithms and data structures.

## **⚙️ System Architecture & Design**

This project is built using **Python (Standard Library)** and **SQLite**. It implements the following computer science concepts:

### **1\. Core Logic (The Controller)**

* **Pattern:** Singleton Design Pattern.  
* **Why:** Ensures a single source of truth for inventory and database connections. It prevents race conditions where two systems might try to assign the same bin simultaneously.

### **2\. Intelligent Storage (Bin Selection)**

* **Algorithm:** Binary Search ($O(\\log N)$).  
* **Logic:** Instead of scanning millions of bins linearly to find a spot for a package, the system keeps bins sorted by capacity and uses Binary Search to instantly find the "Best Fit" (smallest bin that holds the item).

### **3\. Logistics Optimization (Truck Loading)**

* **Algorithm:** Backtracking (Recursion).  
* **Logic:** Solves the "Knapsack-style" problem of fitting a specific set of packages into a truck with limited capacity. It recursively tries combinations to maximize space utilization.

### **4\. Operations Management**

* **Conveyor Belt:** Implemented as a **Queue (FIFO)**. Packages are processed in the exact order they arrive.  
* **Loading Dock:** Implemented as a **Stack (LIFO)**. Allows for rollback\_load() operations—if a loading error occurs, the last item loaded is the first one removed.

### **5\. Persistence**

* **Database:** SQLite (warehouse.db).  
* **Function:** Automatically logs every action (Store/Load/Unload) and maintains the state of bin usage so data survives system restarts.

## **🚀 How to Run**

### **Prerequisites**

* Python 3.x installed.  
* No external libraries required (uses standard sqlite3, queue, abc).

### **Execution**

1. Clone the repository or download warehouse\_system.py.  
2. Run the script:  
   python warehouse\_system.py

3. The script will:  
   * Initialize/Reset the warehouse.db database.  
   * Seed test inventory data.  
   * Run the simulation (Conveyor processing \-\> Truck Optimization \-\> Rollback test).  
   * Print logs to the console.

## **📂 Database Schema**

The system automatically generates a warehouse.db file with the following structure:

**1\. bins**

* bin\_id (Primary Key)  
* capacity (Total size)  
* current\_usage (Occupied space)  
* location\_code (Physical location, e.g., "A1")

**2\. shipment\_logs**

* tracking\_id (Package ID)  
* bin\_id (Where it was stored)  
* timestamp (Time of action)  
* status (STORED, LOADED, UNLOADED\_ROLLBACK)

## **🛠️ Tech Stack**

* **Language:** Python 3  
* **Database:** SQLite  
* **Paradigms:** OOP, Singleton, Recursion