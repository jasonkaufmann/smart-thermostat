import sqlite3
import threading
import logging
import datetime
import time
import pytz
from typing import List, Dict, Optional, Tuple
import uuid
from contextlib import contextmanager

# Database configuration
DB_PATH = 'thermostat_schedules.db'
DB_LOCK = threading.RLock()

# Constants for validation
MIN_TEMPERATURE = 50
MAX_TEMPERATURE = 90
VALID_MODES = ['off', 'heat', 'cool']

# Timezone configuration - change this to your local timezone
LOCAL_TIMEZONE = pytz.timezone('US/Pacific')  # PST/PDT timezone

class SchedulerError(Exception):
    """Custom exception for scheduler-related errors"""
    pass

@contextmanager
def get_db_connection():
    """Thread-safe database connection context manager"""
    with DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

def init_database():
    """Initialize the database with required tables"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create schedules table with better schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedules (
                id TEXT PRIMARY KEY,
                time TEXT NOT NULL,
                temperature INTEGER NOT NULL,
                mode TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                days_of_week TEXT DEFAULT 'daily',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_executed TIMESTAMP,
                next_execution TIMESTAMP,
                retry_count INTEGER DEFAULT 0,
                last_error TEXT,
                CONSTRAINT valid_temperature CHECK (temperature >= 50 AND temperature <= 90),
                CONSTRAINT valid_mode CHECK (mode IN ('off', 'heat', 'cool'))
            )
        ''')
        
        # Create execution history table for tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS execution_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schedule_id TEXT NOT NULL,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success INTEGER NOT NULL,
                error_message TEXT,
                temperature INTEGER,
                mode TEXT,
                FOREIGN KEY (schedule_id) REFERENCES schedules(id) ON DELETE CASCADE
            )
        ''')
        
        # Create index for performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_schedules_next_execution 
            ON schedules(next_execution) WHERE enabled = 1
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_execution_history_schedule_id 
            ON execution_history(schedule_id)
        ''')
        
        conn.commit()
        logging.info("Database initialized successfully")

class ThermostatScheduler:
    def __init__(self, temperature_callback, mode_callback):
        """
        Initialize the scheduler with callbacks for setting temperature and mode
        
        Args:
            temperature_callback: Function to call for setting temperature (temp) -> bool
            mode_callback: Function to call for setting mode (mode) -> bool
        """
        self.temperature_callback = temperature_callback
        self.mode_callback = mode_callback
        self.active_timers = {}
        self.timers_lock = threading.RLock()
        self.running = True
        self.monitor_thread = None
        
        # Initialize database
        init_database()
        
    def start(self):
        """Start the scheduler monitoring thread"""
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_schedules, daemon=True)
        self.monitor_thread.start()
        self._load_all_schedules()
        logging.info("Scheduler started")
        
    def stop(self):
        """Stop the scheduler and clean up"""
        self.running = False
        with self.timers_lock:
            for timer in self.active_timers.values():
                timer.cancel()
            self.active_timers.clear()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logging.info("Scheduler stopped")
        
    def _monitor_schedules(self):
        """Monitor for missed schedules and recovery"""
        while self.running:
            try:
                self._check_missed_schedules()
                self._cleanup_old_history()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logging.error(f"Error in monitor thread: {e}")
                time.sleep(60)
                
    def _check_missed_schedules(self):
        """Check for any missed schedules and execute them"""
        now = datetime.datetime.now(LOCAL_TIMEZONE)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # Find schedules that should have executed but didn't
            cursor.execute('''
                SELECT * FROM schedules 
                WHERE enabled = 1 
                AND next_execution < ? 
                AND (last_executed IS NULL OR last_executed < next_execution)
                ORDER BY next_execution
            ''', (now.isoformat(),))
            
            missed_schedules = cursor.fetchall()
            
            for schedule in missed_schedules:
                logging.warning(f"Found missed schedule {schedule['id']} that should have executed at {schedule['next_execution']}")
                self._execute_schedule(schedule['id'])
                
    def _cleanup_old_history(self):
        """Clean up old execution history (keep last 30 days)"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            thirty_days_ago = datetime.datetime.now(LOCAL_TIMEZONE) - datetime.timedelta(days=30)
            cursor.execute('''
                DELETE FROM execution_history 
                WHERE executed_at < ?
            ''', (thirty_days_ago.isoformat(),))
            conn.commit()
            
    def create_schedule(self, time_str: str, temperature: int, mode: str, 
                       days_of_week: str = 'daily', enabled: bool = True) -> str:
        """
        Create a new schedule
        
        Args:
            time_str: Time in HH:MM format
            temperature: Target temperature (50-90)
            mode: Mode (off, heat, cool)
            days_of_week: Days to run (daily, weekdays, weekends, or comma-separated days)
            enabled: Whether schedule is enabled
            
        Returns:
            Schedule ID
        """
        # Validate inputs
        if not self._validate_time_format(time_str):
            raise SchedulerError("Invalid time format. Use HH:MM")
            
        if not MIN_TEMPERATURE <= temperature <= MAX_TEMPERATURE:
            raise SchedulerError(f"Temperature must be between {MIN_TEMPERATURE} and {MAX_TEMPERATURE}")
            
        if mode.lower() not in VALID_MODES:
            raise SchedulerError(f"Mode must be one of: {', '.join(VALID_MODES)}")
            
        schedule_id = str(uuid.uuid4())
        next_execution = self._calculate_next_execution(time_str, days_of_week)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO schedules (id, time, temperature, mode, enabled, days_of_week, next_execution)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (schedule_id, time_str, temperature, mode.lower(), 
                  1 if enabled else 0, days_of_week, next_execution.isoformat()))
            conn.commit()
            
        if enabled:
            self._schedule_timer(schedule_id, next_execution)
            
        logging.info(f"Created schedule {schedule_id}: {time_str} {temperature}°F {mode}")
        return schedule_id
        
    def update_schedule(self, schedule_id: str, **kwargs):
        """Update an existing schedule"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get current schedule
            cursor.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,))
            schedule = cursor.fetchone()
            if not schedule:
                raise SchedulerError(f"Schedule {schedule_id} not found")
                
            # Build update query
            updates = []
            params = []
            
            if 'time' in kwargs:
                if not self._validate_time_format(kwargs['time']):
                    raise SchedulerError("Invalid time format. Use HH:MM")
                updates.append('time = ?')
                params.append(kwargs['time'])
                
            if 'temperature' in kwargs:
                if not MIN_TEMPERATURE <= kwargs['temperature'] <= MAX_TEMPERATURE:
                    raise SchedulerError(f"Temperature must be between {MIN_TEMPERATURE} and {MAX_TEMPERATURE}")
                updates.append('temperature = ?')
                params.append(kwargs['temperature'])
                
            if 'mode' in kwargs:
                if kwargs['mode'].lower() not in VALID_MODES:
                    raise SchedulerError(f"Mode must be one of: {', '.join(VALID_MODES)}")
                updates.append('mode = ?')
                params.append(kwargs['mode'].lower())
                
            if 'enabled' in kwargs:
                updates.append('enabled = ?')
                params.append(1 if kwargs['enabled'] else 0)
                
            if 'days_of_week' in kwargs:
                updates.append('days_of_week = ?')
                params.append(kwargs['days_of_week'])
                
            if updates:
                updates.append('updated_at = CURRENT_TIMESTAMP')
                
                # Recalculate next execution if time or days changed
                if 'time' in kwargs or 'days_of_week' in kwargs:
                    time_str = kwargs.get('time', schedule['time'])
                    days = kwargs.get('days_of_week', schedule['days_of_week'])
                    next_execution = self._calculate_next_execution(time_str, days)
                    updates.append('next_execution = ?')
                    params.append(next_execution.isoformat())
                    
                params.append(schedule_id)
                query = f"UPDATE schedules SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, params)
                conn.commit()
                
                # Update timer if needed
                self._cancel_timer(schedule_id)
                if kwargs.get('enabled', schedule['enabled']):
                    cursor.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,))
                    updated_schedule = cursor.fetchone()
                    next_exec = datetime.datetime.fromisoformat(updated_schedule['next_execution'])
                    self._schedule_timer(schedule_id, next_exec)
                    
        logging.info(f"Updated schedule {schedule_id}")
        
    def delete_schedule(self, schedule_id: str):
        """Delete a schedule"""
        self._cancel_timer(schedule_id)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM schedules WHERE id = ?', (schedule_id,))
            conn.commit()
            
        logging.info(f"Deleted schedule {schedule_id}")
        
    def get_schedules(self) -> List[Dict]:
        """Get all schedules"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM schedules 
                ORDER BY time, days_of_week
            ''')
            
            schedules = []
            for row in cursor.fetchall():
                schedule = dict(row)
                schedule['enabled'] = bool(schedule['enabled'])
                schedules.append(schedule)
                
            return schedules
            
    def get_schedule_history(self, schedule_id: str, limit: int = 10) -> List[Dict]:
        """Get execution history for a schedule"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM execution_history 
                WHERE schedule_id = ? 
                ORDER BY executed_at DESC 
                LIMIT ?
            ''', (schedule_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
            
    def _validate_time_format(self, time_str: str) -> bool:
        """Validate time format HH:MM"""
        try:
            datetime.datetime.strptime(time_str, '%H:%M')
            return True
        except ValueError:
            return False
            
    def _calculate_next_execution(self, time_str: str, days_of_week: str) -> datetime.datetime:
        """Calculate the next execution time based on schedule settings"""
        now = datetime.datetime.now(LOCAL_TIMEZONE)
        hour, minute = map(int, time_str.split(':'))
        
        # Start with today at the scheduled time
        next_exec = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # If we've already passed today's time, start with tomorrow
        if next_exec <= now:
            next_exec += datetime.timedelta(days=1)
            
        # Handle day of week restrictions
        if days_of_week != 'daily':
            target_days = self._parse_days_of_week(days_of_week)
            
            # Find the next valid day
            for _ in range(7):  # Check up to 7 days ahead
                if next_exec.weekday() in target_days:
                    break
                next_exec += datetime.timedelta(days=1)
                
        return next_exec
        
    def _parse_days_of_week(self, days_str: str) -> List[int]:
        """Parse days of week string into list of weekday numbers"""
        if days_str == 'weekdays':
            return [0, 1, 2, 3, 4]  # Monday to Friday
        elif days_str == 'weekends':
            return [5, 6]  # Saturday and Sunday
        else:
            # Parse comma-separated day names
            day_map = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2,
                'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
            }
            days = []
            for day in days_str.lower().split(','):
                day = day.strip()
                if day in day_map:
                    days.append(day_map[day])
            return days
            
    def _schedule_timer(self, schedule_id: str, execution_time: datetime.datetime):
        """Schedule a timer for the given execution time"""
        now = datetime.datetime.now(LOCAL_TIMEZONE)
        delay = (execution_time - now).total_seconds()
        
        # Check if this is for a 6:00 AM schedule
        is_6am_target = execution_time.hour == 6 and execution_time.minute == 0
        
        if delay > 0:
            timer = threading.Timer(delay, self._execute_schedule, args=(schedule_id,))
            timer.daemon = True
            timer.start()
            
            with self.timers_lock:
                self.active_timers[schedule_id] = timer
            
            if is_6am_target:
                logging.info(f"===== 6:00 AM TIMER SCHEDULED =====")
                logging.info(f"6AM Timer: Schedule ID: {schedule_id}")
                logging.info(f"6AM Timer: Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                logging.info(f"6AM Timer: Execution time: {execution_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                logging.info(f"6AM Timer: Delay: {delay:.0f} seconds ({delay/3600:.1f} hours)")
                logging.info(f"6AM Timer: Timer will fire at: {execution_time}")
            else:
                logging.info(f"Scheduled timer for {schedule_id} at {execution_time} (in {delay:.0f} seconds)")
        else:
            if is_6am_target:
                logging.warning(f"6AM Timer: Cannot schedule - time already passed! Now: {now}, Target: {execution_time}")
            else:
                logging.warning(f"Cannot schedule timer for {schedule_id} - time already passed")
            
    def _cancel_timer(self, schedule_id: str):
        """Cancel an active timer"""
        with self.timers_lock:
            if schedule_id in self.active_timers:
                self.active_timers[schedule_id].cancel()
                del self.active_timers[schedule_id]
                logging.info(f"Cancelled timer for schedule {schedule_id}")
                
    def _execute_schedule(self, schedule_id: str):
        """Execute a scheduled action with retry logic"""
        current_time = datetime.datetime.now(LOCAL_TIMEZONE)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM schedules WHERE id = ?', (schedule_id,))
            schedule = cursor.fetchone()
            
            if not schedule:
                logging.error(f"Schedule {schedule_id} not found in database")
                return
                
            if not schedule['enabled']:
                logging.info(f"Schedule {schedule_id} is disabled, skipping execution")
                return
            
            # Enhanced logging for 6:00 AM schedule
            is_6am_schedule = schedule['time'] == '06:00'
            if is_6am_schedule:
                logging.info(f"===== 6:00 AM SCHEDULE EXECUTION STARTING =====")
                logging.info(f"Schedule ID: {schedule_id}")
                logging.info(f"Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                logging.info(f"Schedule details: {schedule['time']} {schedule['temperature']}°F {schedule['mode']} {schedule['days_of_week']}")
                
            success = False
            error_message = None
            retry_count = schedule['retry_count']
            
            try:
                # Execute mode change first
                if is_6am_schedule:
                    logging.info(f"6AM: Attempting to set mode to {schedule['mode']}")
                    
                mode_success = self.mode_callback(schedule['mode'])
                
                if is_6am_schedule:
                    logging.info(f"6AM: Mode callback returned: {mode_success}")
                    
                if not mode_success:
                    raise SchedulerError(f"Failed to set mode to {schedule['mode']}")
                    
                # Then temperature
                if is_6am_schedule:
                    logging.info(f"6AM: Attempting to set temperature to {schedule['temperature']}°F")
                    
                temp_success = self.temperature_callback(schedule['temperature'])
                
                if is_6am_schedule:
                    logging.info(f"6AM: Temperature callback returned: {temp_success}")
                    
                if not temp_success:
                    raise SchedulerError(f"Failed to set temperature to {schedule['temperature']}")
                    
                success = True
                retry_count = 0  # Reset retry count on success
                
                if is_6am_schedule:
                    logging.info(f"===== 6:00 AM SCHEDULE EXECUTION COMPLETED SUCCESSFULLY =====")
                else:
                    logging.info(f"Successfully executed schedule {schedule_id}: {schedule['temperature']}°F {schedule['mode']}")
                
            except Exception as e:
                error_message = str(e)
                retry_count += 1
                
                if is_6am_schedule:
                    logging.error(f"===== 6:00 AM SCHEDULE EXECUTION FAILED =====")
                    logging.error(f"6AM: Error type: {type(e).__name__}")
                    logging.error(f"6AM: Error message: {error_message}")
                    logging.error(f"6AM: Retry count: {retry_count}")
                    import traceback
                    logging.error(f"6AM: Stack trace:\n{traceback.format_exc()}")
                else:
                    logging.error(f"Failed to execute schedule {schedule_id}: {error_message} (retry count: {retry_count})")
                
                # Schedule retry if under limit
                if retry_count < 3:
                    retry_delay = 60 * (2 ** retry_count)  # Exponential backoff
                    retry_time = datetime.datetime.now(LOCAL_TIMEZONE) + datetime.timedelta(seconds=retry_delay)
                    if is_6am_schedule:
                        logging.info(f"6AM: Scheduling retry in {retry_delay} seconds at {retry_time.strftime('%H:%M:%S')}")
                    self._schedule_timer(schedule_id, retry_time)
                    
            # Update database
            cursor.execute('''
                UPDATE schedules 
                SET last_executed = CURRENT_TIMESTAMP,
                    retry_count = ?,
                    last_error = ?
                WHERE id = ?
            ''', (retry_count, error_message, schedule_id))
            
            # Log execution history
            cursor.execute('''
                INSERT INTO execution_history (schedule_id, success, error_message, temperature, mode)
                VALUES (?, ?, ?, ?, ?)
            ''', (schedule_id, 1 if success else 0, error_message, schedule['temperature'], schedule['mode']))
            
            # Calculate and schedule next execution if successful
            if success:
                next_execution = self._calculate_next_execution(schedule['time'], schedule['days_of_week'])
                cursor.execute('''
                    UPDATE schedules 
                    SET next_execution = ?
                    WHERE id = ?
                ''', (next_execution.isoformat(), schedule_id))
                
                self._schedule_timer(schedule_id, next_execution)
                
            conn.commit()
            
    def _load_all_schedules(self):
        """Load all enabled schedules and set up timers"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM schedules 
                WHERE enabled = 1
            ''')
            
            for schedule in cursor.fetchall():
                if schedule['next_execution']:
                    next_exec = datetime.datetime.fromisoformat(schedule['next_execution'])
                else:
                    next_exec = self._calculate_next_execution(schedule['time'], schedule['days_of_week'])
                    cursor.execute('''
                        UPDATE schedules 
                        SET next_execution = ?
                        WHERE id = ?
                    ''', (next_exec.isoformat(), schedule['id']))
                    
                self._schedule_timer(schedule['id'], next_exec)
                
            conn.commit()
            logging.info(f"Loaded {len(self.active_timers)} active schedules")