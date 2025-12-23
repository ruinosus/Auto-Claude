#!/usr/bin/env python3
"""
Quick test script to verify Azure Foundry authentication is working.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")

def test_auth():
    """Test Azure Foundry authentication configuration."""

    print("🔍 Verificando configuração do Azure Foundry...\n")

    # Check required environment variables
    required_vars = {
        "CLAUDE_CODE_USE_FOUNDRY": os.getenv("CLAUDE_CODE_USE_FOUNDRY"),
        "ANTHROPIC_FOUNDRY_API_KEY": os.getenv("ANTHROPIC_FOUNDRY_API_KEY"),
        "ANTHROPIC_FOUNDRY_BASE_URL": os.getenv("ANTHROPIC_FOUNDRY_BASE_URL"),
        "ANTHROPIC_DEFAULT_SONNET_MODEL": os.getenv("ANTHROPIC_DEFAULT_SONNET_MODEL"),
    }

    print("📋 Variáveis de ambiente:")
    print("-" * 60)

    all_set = True
    for var_name, var_value in required_vars.items():
        if var_value:
            # Mask API key for security
            if "API_KEY" in var_name:
                display_value = f"{var_value[:20]}...{var_value[-10:]}"
            else:
                display_value = var_value
            print(f"✅ {var_name:35} = {display_value}")
        else:
            print(f"❌ {var_name:35} = (não configurada)")
            all_set = False

    print("-" * 60)

    if not all_set:
        print("\n❌ Algumas variáveis necessárias não estão configuradas!")
        return False

    print("\n✅ Todas as variáveis necessárias estão configuradas!")

    # Try to import and configure the auth module
    try:
        from core.auth import get_auth_token, get_sdk_env_vars

        print("\n🔑 Testando autenticação...")
        token = get_auth_token()
        if token:
            print(f"✅ Token encontrado: {token[:20]}...{token[-10:]}")
        else:
            print("❌ Nenhum token encontrado!")
            return False

        print("\n🌐 Variáveis para o SDK:")
        sdk_env = get_sdk_env_vars()
        for key, value in sdk_env.items():
            if "KEY" in key:
                print(f"  {key}: {value[:20]}...{value[-10:]}")
            else:
                print(f"  {key}: {value}")

        print("\n✅ Configuração do Azure Foundry está OK!")
        print("\n💡 Para testar a conexão real, rode:")
        print("   python auto-claude/run.py --list")

        return True

    except Exception as e:
        print(f"\n❌ Erro ao testar autenticação: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_auth()
    sys.exit(0 if success else 1)
