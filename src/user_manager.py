"""
用户管理模块 - 支持多用户的用户系统
"""

import json
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, asdict
from loguru import logger


@dataclass
class User:
    """用户模型"""
    user_id: str
    username: str
    email: str
    password_hash: str
    api_key: str
    created_at: str
    is_active: bool = True
    is_admin: bool = False
    max_websites: int = 8
    max_daily_visits: int = 20
    plan: str = "free"  # free, pro, enterprise


class UserManager:
    """用户管理器"""
    
    def __init__(self, data_dir: str = "data/users"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.users_file = self.data_dir / "users.json"
        self._users: Dict[str, User] = {}
        self._api_key_map: Dict[str, str] = {}  # api_key -> user_id
        
        self._load_users()
    
    def _load_users(self):
        """加载用户数据"""
        if self.users_file.exists():
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for user_data in data.get('users', []):
                        user = User(**user_data)
                        self._users[user.user_id] = user
                        self._api_key_map[user.api_key] = user.user_id
            except Exception as e:
                logger.error(f"加载用户数据失败: {e}")
    
    def _save_users(self):
        """保存用户数据"""
        try:
            data = {
                'users': [asdict(user) for user in self._users.values()],
                'updated_at': datetime.now().isoformat()
            }
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存用户数据失败: {e}")
    
    def _hash_password(self, password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _generate_user_id(self) -> str:
        """生成用户ID"""
        return secrets.token_hex(8)
    
    def _generate_api_key(self) -> str:
        """生成API密钥"""
        return f"seo_{secrets.token_hex(16)}"
    
    def register(self, username: str, email: str, password: str) -> Optional[User]:
        """
        注册用户
        
        Args:
            username: 用户名
            email: 邮箱
            password: 密码
            
        Returns:
            新用户对象，如果注册失败返回None
        """
        # 检查用户名是否已存在
        for user in self._users.values():
            if user.username == username or user.email == email:
                logger.warning(f"用户名或邮箱已存在: {username}, {email}")
                return None
        
        # 创建新用户
        user_id = self._generate_user_id()
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=self._hash_password(password),
            api_key=self._generate_api_key(),
            created_at=datetime.now().isoformat()
        )
        
        self._users[user_id] = user
        self._api_key_map[user.api_key] = user_id
        self._save_users()
        
        # 创建用户数据目录
        self._create_user_data_dir(user_id)
        
        logger.info(f"新用户注册成功: {username}")
        return user
    
    def login(self, username: str, password: str) -> Optional[User]:
        """
        用户登录
        
        Args:
            username: 用户名或邮箱
            password: 密码
            
        Returns:
            用户对象，如果登录失败返回None
        """
        password_hash = self._hash_password(password)
        
        for user in self._users.values():
            if (user.username == username or user.email == username) and \
               user.password_hash == password_hash and \
               user.is_active:
                logger.info(f"用户登录成功: {username}")
                return user
        
        logger.warning(f"登录失败: {username}")
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """通过ID获取用户"""
        return self._users.get(user_id)
    
    def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """通过API密钥获取用户"""
        user_id = self._api_key_map.get(api_key)
        if user_id:
            return self._users.get(user_id)
        return None
    
    def regenerate_api_key(self, user_id: str) -> Optional[str]:
        """重新生成API密钥"""
        user = self._users.get(user_id)
        if user:
            # 删除旧映射
            del self._api_key_map[user.api_key]
            # 生成新密钥
            user.api_key = self._generate_api_key()
            self._api_key_map[user.api_key] = user_id
            self._save_users()
            return user.api_key
        return None
    
    def update_user_plan(self, user_id: str, plan: str, max_websites: int = None, max_daily_visits: int = None):
        """更新用户套餐"""
        user = self._users.get(user_id)
        if user:
            user.plan = plan
            if max_websites:
                user.max_websites = max_websites
            if max_daily_visits:
                user.max_daily_visits = max_daily_visits
            self._save_users()
            logger.info(f"用户 {user.username} 套餐已更新为 {plan}")
    
    def _create_user_data_dir(self, user_id: str):
        """创建用户数据目录"""
        user_dir = Path(f"data/user_data/{user_id}")
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        (user_dir / "config").mkdir(exist_ok=True)
        (user_dir / "logs").mkdir(exist_ok=True)
        (user_dir / "stats").mkdir(exist_ok=True)
        
        # 创建默认配置文件
        default_websites = {
            "websites": []
        }
        with open(user_dir / "config" / "websites.json", 'w', encoding='utf-8') as f:
            json.dump(default_websites, f, ensure_ascii=False, indent=2)
    
    def get_user_data_dir(self, user_id: str) -> Path:
        """获取用户数据目录"""
        return Path(f"data/user_data/{user_id}")
    
    def list_all_users(self) -> List[User]:
        """获取所有用户列表（管理员用）"""
        return list(self._users.values())


# 全局用户管理器
user_manager = UserManager()
