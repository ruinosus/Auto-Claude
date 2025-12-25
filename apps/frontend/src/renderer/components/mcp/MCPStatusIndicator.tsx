import type { MCPServerStatus } from '../../../shared/types/mcp';

interface MCPStatusIndicatorProps {
  status: MCPServerStatus;
  className?: string;
}

export function MCPStatusIndicator({ status, className = '' }: MCPStatusIndicatorProps) {
  const statusConfig = {
    connected: { icon: '🟢', label: 'Active', color: 'text-green-600' },
    connecting: { icon: '🟡', label: 'Connecting', color: 'text-yellow-600' },
    error: { icon: '🔴', label: 'Error', color: 'text-red-600' },
    disabled: { icon: '⚪', label: 'Disabled', color: 'text-gray-400' },
    disconnected: { icon: '🔴', label: 'Disconnected', color: 'text-red-600' }
  };

  const config = statusConfig[status] || { icon: '⚪', label: status || 'Unknown', color: 'text-gray-400' };

  return (
    <span className={`inline-flex items-center gap-1 text-sm font-medium ${config.color} ${className}`}>
      <span>{config.icon}</span>
      <span>{config.label}</span>
    </span>
  );
}
