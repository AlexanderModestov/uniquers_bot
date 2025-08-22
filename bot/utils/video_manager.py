import json
import os
import logging

logger = logging.getLogger(__name__)

def get_video_name(filename: str, field='name') -> str:
    """
    Get video name from video_descriptions.json file.
    Falls back to filename if no description found.
    """
    try:
        json_path = os.path.join('configs', 'video_descriptions.json')
        with open(json_path, 'r', encoding='utf-8') as file:
            video_descriptions = json.load(file)['videos']
            
        # Get video info from descriptions
        video_info = video_descriptions.get(filename.split('.')[0])
        if video_info and video_info.get(field):
            return video_info[field]
            
        # Fallback to filename if no description found
        return filename
        
    except Exception as e:
        logger.error(f"Error getting video name from descriptions: {e}")
        return filename

def get_video_info(filename: str) -> dict:
    """
    Get full video information from video_descriptions.json file.
    Returns None if no information found.
    """
    try:
        # Remove file extension if present
        video_name = filename.split('.')[0] if '.' in filename else filename
        
        json_path = os.path.join('configs', 'video_descriptions.json')
        with open(json_path, 'r', encoding='utf-8') as file:
            video_descriptions = json.load(file)['videos']
            
        # Get video info from descriptions
        video_info = video_descriptions.get(video_name)
        
        if not video_info:
            logger.warning(f"No video info found for {filename}")
            return None
            
        # Ensure all required fields exist
        default_info = {
            'name': video_name,
            'short_description': 'No description available',
            'long_description': 'No detailed description available'
        }
        
        # Merge default with actual info
        for key, value in default_info.items():
            if key not in video_info or not video_info[key]:
                video_info[key] = value
                
        return video_info
        
    except Exception as e:
        logger.error(f"Error getting video info from descriptions: {e}")
        return None