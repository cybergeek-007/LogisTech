import sqlite3
from datetime import datetime
from queue import Queue
from abc import ABC, abstractmethod

# Database file
DB_NAME = 'warehouse.db'


class WarehouseController:
    _instance = None

    # Singleton pattern implementation
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WarehouseController, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.bins = []
        self.conveyor = Queue()
        self.truck_stack = []  # LIFO stack for the truck
        self.conn = None

        self.connect_db()
        self._initialized = True

    def connect_db(self):
        self.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        cursor = self.conn.cursor()

        # Resetting table for a clean run every time
        cursor.execute('DROP TABLE IF EXISTS bins')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shipment_logs (
                tracking_id TEXT,
                bin_id INTEGER,
                timestamp TEXT,
                status TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bins (
                bin_id INTEGER PRIMARY KEY,
                capacity INTEGER,
                current_usage INTEGER DEFAULT 0,
                location_code TEXT
            )
        ''')
        self.conn.commit()

    def load_inventory(self):
        # Fetch bins from SQL and sort them for Binary Search
        cursor = self.conn.cursor()
        cursor.execute('SELECT bin_id, capacity, current_usage, location_code FROM bins')
        rows = cursor.fetchall()

        self.bins = []
        for r in rows:
            b = StorageBin(r[0], r[1], r[3])
            b.used_space = r[2]
            self.bins.append(b)

        # Sort is required for binary search to work
        self.bins.sort()

    def add_to_conveyor(self, pkg):
        self.conveyor.put(pkg)

    def run_conveyor(self):
        print(f"\n[Conveyor] Processing {self.conveyor.qsize()} items...")

        while not self.conveyor.empty():
            pkg = self.conveyor.get()
            target_bin = self.find_bin_binary_search(pkg)

            if target_bin:
                try:
                    target_bin.occupy_space(pkg.size)
                    self.update_bin_db(target_bin)
                    self.log_action(pkg.tracking_id, target_bin.bin_id, 'STORED')
                    print(f" -> Stored {pkg.tracking_id} (Size {pkg.size}) in Bin {target_bin.bin_id}")
                except Exception as e:
                    print(f" -> Error storing {pkg.tracking_id}: {e}")
            else:
                print(f" -> FAIL: No suitable bin for {pkg.tracking_id} (Size {pkg.size})")

    def find_bin_binary_search(self, pkg):
        # O(log N) search for the best fit
        low = 0
        high = len(self.bins) - 1
        best_fit = None

        while low <= high:
            mid = (low + high) // 2
            curr = self.bins[mid]

            # We need a bin that fits the size AND has space remaining
            if curr.capacity >= pkg.size and curr.available_space() >= pkg.size:
                best_fit = curr
                high = mid - 1  # Try to find a smaller bin that still fits (optimize space)
            else:
                low = mid + 1

        return best_fit

    def load_truck(self, pkg):
        self.truck_stack.append(pkg)
        self.log_action(pkg.tracking_id, None, 'LOADED_ON_TRUCK')
        print(f"Loaded {pkg.tracking_id} onto truck.")

    def undo_last_load(self):
        if self.truck_stack:
            pkg = self.truck_stack.pop()
            self.log_action(pkg.tracking_id, None, 'REMOVED_FROM_TRUCK')
            print(f"Undo: Removed {pkg.tracking_id} from truck.")
            return pkg
        print("Truck is empty, nothing to undo.")
        return None

    def optimize_truck_space(self, packages, max_cap):
        # Backtracking algorithm to fill truck efficiently
        best_combo = []
        max_filled = 0

        def solve(idx, current_combo, current_size):
            nonlocal best_combo, max_filled

            if current_size > max_filled:
                max_filled = current_size
                best_combo = list(current_combo)

            if idx == len(packages):
                return

            pkg = packages[idx]

            # Option 1: Take the package (if it fits)
            if current_size + pkg.size <= max_cap:
                current_combo.append(pkg)
                solve(idx + 1, current_combo, current_size + pkg.size)
                current_combo.pop()  # Backtrack

            # Option 2: Skip the package
            solve(idx + 1, current_combo, current_size)

        solve(0, [], 0)
        return best_combo

    def update_bin_db(self, bin_obj):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE bins SET current_usage = ? WHERE bin_id = ?',
                       (bin_obj.used_space, bin_obj.bin_id))
        self.conn.commit()

    def log_action(self, tracking_id, bin_id, status):
        try:
            cursor = self.conn.cursor()
            cursor.execute('INSERT INTO shipment_logs VALUES (?, ?, ?, ?)',
                           (tracking_id, bin_id, datetime.now().isoformat(), status))
            self.conn.commit()
        except Exception as e:
            print(f"Logging failed: {e}")


# --- Models ---

class StorageUnit(ABC):
    @abstractmethod
    def occupy_space(self, amount): pass

    @abstractmethod
    def available_space(self): pass


class StorageBin(StorageUnit):
    def __init__(self, bin_id, capacity, location_code):
        self.bin_id = bin_id
        self.capacity = capacity
        self.location_code = location_code
        self.used_space = 0

    def occupy_space(self, amount):
        if self.used_space + amount > self.capacity:
            raise ValueError("Bin Full")
        self.used_space += amount

    def available_space(self):
        return self.capacity - self.used_space

    # Needed for sorting
    def __lt__(self, other):
        return self.capacity < other.capacity


class Package:
    def __init__(self, tracking_id, size, destination):
        self.tracking_id = tracking_id
        self.size = size
        self.destination = destination


# --- Helper to populate DB ---

def seed_database(ctrl):
    cursor = ctrl.conn.cursor()
    # Pre-defined bins: Small to Large
    data = [
        (1, 50, 0, 'A1'),
        (2, 100, 0, 'A2'),
        (3, 150, 0, 'B1'),
        (4, 200, 0, 'B2'),
        (5, 500, 0, 'C1')
    ]
    cursor.executemany('INSERT INTO bins VALUES (?, ?, ?, ?)', data)
    ctrl.conn.commit()
    ctrl.load_inventory()  # Refresh memory
    print("Database seeded with empty bins.")


# --- Main Execution ---

if __name__ == '__main__':
    system = WarehouseController()
    seed_database(system)

    # 1. Inbound: Packages arrive on conveyor
    incoming = [
        Package('PKG_SMALL', 45, 'NY'),
        Package('PKG_HUGE', 120, 'CA'),
        Package('PKG_MID', 30, 'TX')
    ]

    for p in incoming:
        system.add_to_conveyor(p)

    # Process them using Binary Search
    system.run_conveyor()

    # 2. Outbound: Optimize Truck Loading (Backtracking)
    print("\n[Truck Loading] Calculating best fit for capacity 100...")

    # Scenario: We have 50, 60, and 40.
    # 50+60 = 110 (Fail). 50+40 = 90. 60+40 = 100 (Winner).
    cargo_list = [
        Package('BOX_A', 50, 'NY'),
        Package('BOX_B', 60, 'CA'),
        Package('BOX_C', 40, 'TX')
    ]

    optimized_load = system.optimize_truck_space(cargo_list, 100)

    print("Best Combination found:")
    for p in optimized_load:
        system.load_truck(p)

    # 3. Mistake handling (LIFO Stack)
    print("\n[Correction] Removing last item...")
    system.undo_last_load()