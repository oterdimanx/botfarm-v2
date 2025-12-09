import sqlite3
import os
from datetime import datetime

class DatabaseGuardian:
    def __init__(self, db_file='data/bot_world.db'):
        self.db_file = db_file
        self.alerts = []
    
    def check_database_health(self):
        """Perform comprehensive database health check"""
        checks = {}
        
        # Check database size
        checks['database_size'] = self._check_database_size()
        
        # Check table sizes
        checks['table_sizes'] = self._check_table_sizes()
        
        # Check bot statistics
        checks['bot_stats'] = self._check_bot_statistics()
        
        # Check memory usage
        checks['memory_usage'] = self._check_memory_usage()
        
        # Check for orphans/integrity
        checks['integrity'] = self._check_integrity()
        
        return checks
    
    def _check_database_size(self):
        """Check the physical database file size"""
        size_bytes = os.path.getsize(self.db_file)
        size_mb = size_bytes / (1024 * 1024)
        
        status = "NORMAL"
        if size_mb > 10:  # 10MB threshold
            status = "WARNING"
        if size_mb > 50:  # 50MB threshold  
            status = "CRITICAL"
        
        return {
            'size_mb': round(size_mb, 2),
            'status': status,
            'message': f"Database size: {size_mb:.2f}MB"
        }
    
    def _check_table_sizes(self):
        """Check the size of each table"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        tables = ['bots', 'personality', 'knowledge', 'memory', 'needs', 'skills']
        table_sizes = {}
        
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            
            status = "NORMAL"
            if table == 'memory' and count > 1000:
                status = "WARNING"
            elif table == 'knowledge' and count > 500:
                status = "WARNING"
            
            table_sizes[table] = {
                'count': count,
                'status': status
            }
        
        conn.close()
        return table_sizes
    
    def _check_bot_statistics(self):
        """Check statistics for each bot"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT b.id, b.name, 
                   COUNT(DISTINCT k.id) as knowledge_count,
                   COUNT(DISTINCT m.id) as memory_count,
                   AVG(n.value) as avg_need
            FROM bots b
            LEFT JOIN knowledge k ON b.id = k.bot_id
            LEFT JOIN memory m ON b.id = m.bot_id
            LEFT JOIN needs n ON b.id = n.bot_id
            WHERE b.is_active = 1
            GROUP BY b.id
        ''')
        
        bot_stats = {}
        for bot_id, name, knowledge_count, memory_count, avg_need in cursor.fetchall():
            issues = []
            
            if knowledge_count == 0:
                issues.append("No knowledge")
            if memory_count > 500:
                issues.append("High memory usage")
            if avg_need and avg_need < 20:
                issues.append("Low needs")
            
            status = "HEALTHY" if not issues else "CONCERN"
            
            bot_stats[name] = {
                'knowledge_count': knowledge_count,
                'memory_count': memory_count,
                'avg_need': round(avg_need, 2) if avg_need else 0,
                'issues': issues,
                'status': status
            }
        
        conn.close()
        return bot_stats
    
    def _check_memory_usage(self):
        """Check memory table usage"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM memory')
        total_memories = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT b.name, COUNT(m.id) as memory_count
            FROM bots b
            LEFT JOIN memory m ON b.id = m.bot_id
            GROUP BY b.id
            ORDER BY memory_count DESC
        ''')
        
        memory_by_bot = cursor.fetchall()
        conn.close()
        
        status = "NORMAL"
        if total_memories > 2000:
            status = "CRITICAL"
        elif total_memories > 1000:
            status = "WARNING"
        
        return {
            'total_memories': total_memories,
            'status': status,
            'by_bot': memory_by_bot
        }
    
    def _check_integrity(self):
        """Check database integrity"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Check for orphaned records
        integrity_issues = []
        
        # Check knowledge without bots
        cursor.execute('SELECT k.id FROM knowledge k LEFT JOIN bots b ON k.bot_id = b.id WHERE b.id IS NULL')
        if cursor.fetchone():
            integrity_issues.append("Orphaned knowledge records")
        
        # Check memory without bots
        cursor.execute('SELECT m.id FROM memory m LEFT JOIN bots b ON m.bot_id = b.id WHERE b.id IS NULL')
        if cursor.fetchone():
            integrity_issues.append("Orphaned memory records")
        
        conn.close()
        
        return {
            'issues': integrity_issues,
            'status': "HEALTHY" if not integrity_issues else "ISSUES"
        }
    
    def generate_guardian_report(self):
        """Generate a comprehensive guardian report"""
        health_check = self.check_database_health()
        
        report = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'overall_status': 'HEALTHY',
            'alerts': [],
            'details': health_check
        }
        
        # Check for critical issues
        if health_check['database_size']['status'] == "CRITICAL":
            report['alerts'].append("🚨 DATABASE SIZE CRITICAL - Consider archiving old data")
            report['overall_status'] = 'CRITICAL'
        
        if health_check['memory_usage']['status'] == "CRITICAL":
            report['alerts'].append("🚨 MEMORY USAGE CRITICAL - Too many memories stored")
            report['overall_status'] = 'CRITICAL'
        
        # Check for warnings
        if health_check['database_size']['status'] == "WARNING":
            report['alerts'].append("⚠️ Database growing large - Monitor closely")
            if report['overall_status'] == 'HEALTHY':
                report['overall_status'] = 'WARNING'
        
        # Check bot health
        for bot_name, stats in health_check['bot_stats'].items():
            if stats['status'] == "CONCERN":
                report['alerts'].append(f"⚠️ {bot_name} has issues: {', '.join(stats['issues'])}")
                if report['overall_status'] == 'HEALTHY':
                    report['overall_status'] = 'WARNING'
        
        return report
    
    def get_guardian_message(self, report):
        """Convert report into a roleplayed guardian message"""
        if report['overall_status'] == 'CRITICAL':
            urgency = "URGENT"
            icon = "🚨"
        elif report['overall_status'] == 'WARNING':
            urgency = "ATTENTION"
            icon = "⚠️"
        else:
            urgency = "STATUS"
            icon = "✅"
        
        message = f"{icon} **DATABASE GUARDIAN REPORT** {icon}\n"
        message += f"**Status**: {urgency}\n"
        message += f"**Time**: {report['timestamp']}\n\n"
        
        if report['alerts']:
            message += "**ALERTS**:\n"
            for alert in report['alerts']:
                message += f"• {alert}\n"
            message += "\n"
        
        # Add key statistics
        db_size = report['details']['database_size']
        memory_usage = report['details']['memory_usage']
        
        message += "**KEY METRICS**:\n"
        message += f"• Database Size: {db_size['size_mb']}MB ({db_size['status']})\n"
        message += f"• Total Memories: {memory_usage['total_memories']} ({memory_usage['status']})\n"
        
        # Bot status summary
        healthy_bots = sum(1 for stats in report['details']['bot_stats'].values() if stats['status'] == 'HEALTHY')
        total_bots = len(report['details']['bot_stats'])
        
        message += f"• Bots Healthy: {healthy_bots}/{total_bots}\n"
        
        return message

# Test the guardian
if __name__ == "__main__":
    guardian = DatabaseGuardian()
    report = guardian.generate_guardian_report()
    message = guardian.get_guardian_message(report)
    print(message)