"""共享测试夹具"""

import pytest
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.safety.rbac import UserContext, Role


@pytest.fixture
def viewer_user():
    return UserContext(user_id="test_viewer", role=Role.VIEWER)


@pytest.fixture
def operator_user():
    return UserContext(user_id="test_operator", role=Role.OPERATOR)


@pytest.fixture
def admin_user():
    return UserContext(user_id="test_admin", role=Role.ADMIN)
