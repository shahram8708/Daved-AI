
from app import db
from app.models import FeatureFlag
from datetime import datetime, timedelta
from app.cache import cache

@cache.memoize(timeout=60)
def is_feature_enabled(feature_name):
    
    flag = FeatureFlag.query.filter_by(name=feature_name).first()
    return flag.is_enabled if flag else False

def set_feature_flag(feature_name, enabled, description=None):
    
    flag = FeatureFlag.query.filter_by(name=feature_name).first()
    
    if not flag:
        flag = FeatureFlag(name=feature_name, is_enabled=enabled, description=description)
    else:
        flag.is_enabled = enabled
        if description:
            flag.description = description
    
    db.session.add(flag)
    db.session.commit()
    
    
    cache.delete_memoized(is_feature_enabled, feature_name)
    return flag