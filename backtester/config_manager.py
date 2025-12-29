"""
配置管理模块

负责策略参数配置的保存、加载和管理。
支持多配置方案，可按策略/股票组合保存不同的参数配置。
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import uuid


class ConfigManager:
    """
    配置管理器
    
    管理策略参数配置的持久化存储。
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置目录路径，默认为 configs/strategies/
        """
        if config_dir is None:
            project_root = Path(__file__).parent.parent
            config_dir = project_root / 'configs' / 'strategies'
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_id(self) -> str:
        """生成唯一配置ID"""
        return str(uuid.uuid4())[:8]
    
    def _get_config_path(self, config_id: str) -> Path:
        """获取配置文件路径"""
        return self.config_dir / f"{config_id}.json"
    
    def save_config(self, 
                    strategy: str,
                    params: Dict[str, Any],
                    name: Optional[str] = None,
                    symbol: Optional[str] = None,
                    config_id: Optional[str] = None,
                    description: Optional[str] = None) -> Dict[str, Any]:
        """
        保存配置
        
        Args:
            strategy: 策略模块名
            params: 策略参数字典
            name: 配置名称（可选）
            symbol: 关联的股票代码（可选）
            config_id: 配置ID（如果提供则更新现有配置）
            description: 配置描述（可选）
        
        Returns:
            保存的配置信息
        """
        now = datetime.now().isoformat()
        
        # 生成或使用现有ID
        if config_id is None:
            config_id = self._generate_id()
            created_at = now
        else:
            # 尝试读取现有配置的创建时间
            existing = self.get_config(config_id)
            created_at = existing.get('created_at', now) if existing else now
        
        # 自动生成名称
        if name is None:
            name = f"{strategy}"
            if symbol:
                name += f" - {symbol}"
        
        config = {
            'id': config_id,
            'name': name,
            'strategy': strategy,
            'symbol': symbol,
            'params': params,
            'description': description,
            'created_at': created_at,
            'updated_at': now
        }
        
        # 保存到文件
        config_path = self._get_config_path(config_id)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return config
    
    def get_config(self, config_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定配置
        
        Args:
            config_id: 配置ID
        
        Returns:
            配置字典，不存在则返回None
        """
        config_path = self._get_config_path(config_id)
        
        if not config_path.exists():
            return None
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def delete_config(self, config_id: str) -> bool:
        """
        删除配置
        
        Args:
            config_id: 配置ID
        
        Returns:
            是否删除成功
        """
        config_path = self._get_config_path(config_id)
        
        if config_path.exists():
            config_path.unlink()
            return True
        return False
    
    def list_configs(self, 
                     strategy: Optional[str] = None,
                     symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出所有配置
        
        Args:
            strategy: 按策略筛选（可选）
            symbol: 按股票筛选（可选）
        
        Returns:
            配置列表
        """
        configs = []
        
        for config_file in self.config_dir.glob('*.json'):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                    # 筛选
                    if strategy and config.get('strategy') != strategy:
                        continue
                    if symbol and config.get('symbol') != symbol:
                        continue
                    
                    configs.append(config)
            except Exception:
                continue
        
        # 按更新时间排序（最新的在前）
        configs.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        
        return configs
    
    def get_configs_by_strategy(self, strategy: str) -> List[Dict[str, Any]]:
        """获取指定策略的所有配置"""
        return self.list_configs(strategy=strategy)
    
    def get_configs_by_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """获取指定股票的所有配置"""
        return self.list_configs(symbol=symbol)
    
    def duplicate_config(self, config_id: str, new_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        复制配置
        
        Args:
            config_id: 要复制的配置ID
            new_name: 新配置名称
        
        Returns:
            新配置信息
        """
        original = self.get_config(config_id)
        if not original:
            return None
        
        if new_name is None:
            new_name = f"{original.get('name', 'Config')} (副本)"
        
        return self.save_config(
            strategy=original['strategy'],
            params=original['params'],
            name=new_name,
            symbol=original.get('symbol'),
            description=original.get('description')
        )
    
    def export_config(self, config_id: str) -> Optional[str]:
        """
        导出配置为JSON字符串
        
        Args:
            config_id: 配置ID
        
        Returns:
            JSON字符串
        """
        config = self.get_config(config_id)
        if config:
            return json.dumps(config, indent=2, ensure_ascii=False)
        return None
    
    def import_config(self, json_str: str) -> Optional[Dict[str, Any]]:
        """
        从JSON字符串导入配置
        
        Args:
            json_str: JSON字符串
        
        Returns:
            导入的配置信息
        """
        try:
            data = json.loads(json_str)
            
            # 验证必要字段
            if 'strategy' not in data or 'params' not in data:
                return None
            
            # 生成新ID（避免覆盖）
            return self.save_config(
                strategy=data['strategy'],
                params=data['params'],
                name=data.get('name'),
                symbol=data.get('symbol'),
                description=data.get('description')
            )
        except Exception:
            return None
    
    def get_latest_config(self, strategy: str, symbol: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        获取最新的配置
        
        Args:
            strategy: 策略名称
            symbol: 股票代码（可选）
        
        Returns:
            最新的配置
        """
        configs = self.list_configs(strategy=strategy, symbol=symbol)
        return configs[0] if configs else None


# 便捷函数
def save_strategy_config(strategy: str, params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """快速保存策略配置"""
    manager = ConfigManager()
    return manager.save_config(strategy, params, **kwargs)


def load_strategy_config(config_id: str) -> Optional[Dict[str, Any]]:
    """快速加载策略配置"""
    manager = ConfigManager()
    return manager.get_config(config_id)


def list_strategy_configs(strategy: Optional[str] = None) -> List[Dict[str, Any]]:
    """列出策略配置"""
    manager = ConfigManager()
    return manager.list_configs(strategy=strategy)

