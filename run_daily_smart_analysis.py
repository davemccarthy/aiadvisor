#!/usr/bin/env python3
"""
Daily Smart Analysis Runner

This script runs the Smart Analysis once per day at startup.
It checks if analysis has already been run today to avoid duplicates.
"""

import os
import sys
import django
from datetime import datetime, date
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aiadvisor.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from soulstrader.models import SmartAnalysisSession
from soulstrader.smart_analysis_service import SmartAnalysisService
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/daily_smart_analysis.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def has_analysis_run_today():
    """Check if Smart Analysis has already been run today"""
    today = timezone.now().date()
    
    # Check if any successful analysis sessions exist for today
    sessions_today = SmartAnalysisSession.objects.filter(
        started_at__date=today,
        status='COMPLETED'
    )
    
    return sessions_today.exists()


def run_daily_smart_analysis():
    """Run Smart Analysis for all active users"""
    
    # SAFETY CHECK: Disable automated Smart Analysis to conserve trial API calls
    logger.info("Smart Analysis is DISABLED to conserve trial API calls")
    logger.info("To enable automated analysis, remove this safety check")
    return
    
    logger.info("Starting Daily Smart Analysis")
    
    # Check if analysis has already been run today
    if has_analysis_run_today():
        logger.info("Smart Analysis already run today. Skipping.")
        return
    
    # Get all active users with portfolios
    users = User.objects.filter(
        is_active=True,
        portfolio__isnull=False
    ).distinct()
    
    if not users.exists():
        logger.warning("No active users with portfolios found")
        return
    
    logger.info(f"Found {users.count()} active users with portfolios")
    
    # Initialize Smart Analysis Service
    smart_service = SmartAnalysisService()
    
    successful_analyses = 0
    failed_analyses = 0
    
    # Run analysis for each user
    for user in users:
        try:
            logger.info(f"Running Smart Analysis for user: {user.username}")
            
            # Run analysis (without auto-execute for safety)
            session = smart_service.smart_analyse(user=user, auto_execute=False)
            
            if session.status == 'COMPLETED':
                successful_analyses += 1
                logger.info(f"✓ Analysis completed for {user.username}: "
                           f"{session.total_recommendations} recommendations")
            else:
                failed_analyses += 1
                logger.error(f"✗ Analysis failed for {user.username}: {session.error_message}")
                
        except Exception as e:
            failed_analyses += 1
            logger.error(f"✗ Analysis failed for {user.username}: {str(e)}")
            continue
    
    # Summary
    logger.info(f"Daily Smart Analysis completed:")
    logger.info(f"  Successful: {successful_analyses}")
    logger.info(f"  Failed: {failed_analyses}")
    logger.info(f"  Total: {successful_analyses + failed_analyses}")


if __name__ == "__main__":
    try:
        run_daily_smart_analysis()
    except Exception as e:
        logger.error(f"Daily Smart Analysis failed: {str(e)}")
        sys.exit(1)
