'use client';

import { useEffect, useState } from 'react';
import { Settings } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';

interface AgentStatus {
  name: string;
  agent_id: string;
  enabled: boolean;
  status: 'healthy' | 'degraded' | 'unavailable';
  model: string;
  description: string;
  icon: string;
  color: string;
}

interface AgentHealthResponse {
  agents: AgentStatus[];
  total_count: number;
  healthy_count: number;
  degraded_count: number;
  unavailable_count: number;
}

interface AgentManagerProps {
  blueprint: string;
  sessionId: string | null;
}

const StatusBadge = ({ status }: { status: string }) => {
  const variants = {
    healthy: 'bg-green-500/10 text-green-600 border-green-500/20',
    degraded: 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20',
    unavailable: 'bg-red-500/10 text-red-600 border-red-500/20',
  };
  
  return (
    <Badge 
      variant="outline" 
      className={`text-xs capitalize ${variants[status as keyof typeof variants] || 'bg-gray-500/10 text-gray-600'}`}
    >
      {status}
    </Badge>
  );
};

export function AgentManager({ blueprint, sessionId }: AgentManagerProps) {
  const [agentsHealth, setAgentsHealth] = useState<AgentHealthResponse | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(true);
  const [mounted, setMounted] = useState(false);

  // Prevent hydration mismatch - only render after client mount
  useEffect(() => {
    setMounted(true);
  }, []);

  const fetchAgentsStatus = async () => {
    try {
      // Use NEXT_PUBLIC_ prefixed env var for client-side access
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || 'http://localhost:8001';
      
      // Use consistent session ID - "default" if none provided
      const effectiveSessionId = sessionId || 'default';
      const url = `${apiUrl}/api/blueprints/${blueprint}/agents/status?session_id=${effectiveSessionId}&t=${Date.now()}`;
      
      console.log('Fetching agent status from:', url);
      const response = await fetch(url, {
        cache: 'no-store',
        headers: {
          'Cache-Control': 'no-cache',
        },
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Received agent status:', data);
        setAgentsHealth(data);
      }
    } catch (error) {
      console.error('Failed to fetch agents status:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (!mounted) return;
    fetchAgentsStatus();
    // Refresh status every 30 seconds
    const interval = setInterval(fetchAgentsStatus, 30000);
    return () => clearInterval(interval);
  }, [blueprint, sessionId, mounted]);

  const toggleAgent = async (
    agentId: string,
    agentName: string,
    currentEnabled: boolean
  ) => {
    // Supervisor cannot be disabled
    if (agentName.toLowerCase() === 'supervisor') {
      console.log('Supervisor cannot be disabled');
      return;
    }

    try {
      // Use consistent session ID - if none, use "default" to match backend
      const effectiveSessionId = sessionId || 'default';
      
      console.log('Toggling agent:', agentId, 'from', currentEnabled, 'to', !currentEnabled, 'session:', effectiveSessionId);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || 'http://localhost:8001';
      const response = await fetch(
        `${apiUrl}/api/blueprints/${blueprint}/agents/${agentId}/toggle`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: effectiveSessionId,
            enabled: !currentEnabled,
          }),
        }
      );
      
      if (response.ok) {
        const result = await response.json();
        console.log('Toggle result:', result);
        
        // Immediately update local state for instant UI feedback
        // Only update the enabled flag, keep health status unchanged
        setAgentsHealth((prev) => {
          if (!prev) return prev;
          const newState = {
            ...prev,
            agents: prev.agents.map((agent) =>
              agent.agent_id === agentId
                ? { ...agent, enabled: !currentEnabled }
                : agent
            ),
          };
          console.log('Optimistic update applied:', newState);
          return newState;
        });
        
        // Then fetch fresh data from server with same session ID
        setTimeout(() => {
          console.log('Fetching fresh status...');
          fetchAgentsStatus();
        }, 500);
      } else {
        console.error('Toggle failed:', await response.text());
      }
    } catch (error) {
      console.error('Failed to toggle agent:', error);
    }
  };

  // Don't render until mounted to avoid hydration mismatch
  if (!mounted || isLoading || !agentsHealth) {
    return (
      <Button variant="outline" size="sm" disabled>
        <Settings className="h-4 w-4" />
      </Button>
    );
  }

  const { healthy_count, degraded_count, unavailable_count } = agentsHealth;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Settings className="h-4 w-4" />
          <span className="text-xs">Agents</span>
          <div className="flex gap-1">
            {healthy_count > 0 && (
              <Badge variant="outline" className="h-5 px-1.5 text-xs bg-green-500/10 text-green-600 border-green-500/20">
                {healthy_count}
              </Badge>
            )}
            {degraded_count > 0 && (
              <Badge variant="outline" className="h-5 px-1.5 text-xs bg-yellow-500/10 text-yellow-600 border-yellow-500/20">
                {degraded_count}
              </Badge>
            )}
            {unavailable_count > 0 && (
              <Badge variant="outline" className="h-5 px-1.5 text-xs bg-red-500/10 text-red-600 border-red-500/20">
                {unavailable_count}
              </Badge>
            )}
          </div>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel>Agent Status</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {agentsHealth.agents.map((agent) => {
          const isSupervisor = agent.name.toLowerCase() === 'supervisor';
          
          return (
            <DropdownMenuItem
              key={agent.agent_id}
              className="flex items-start gap-3 p-3 cursor-pointer hover:bg-accent"
              onSelect={(e) => {
                e.preventDefault();
              }}
            >
              {/* Checkbox for enable/disable */}
              <div className="pt-0.5">
                <Checkbox
                  checked={agent.enabled}
                  disabled={isSupervisor}
                  onCheckedChange={(checked) => {
                    toggleAgent(agent.agent_id, agent.name, agent.enabled);
                  }}
                  className="h-5 w-5"
                />
              </div>
              
              {/* Agent info */}
              <div className="flex-1 space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{agent.icon}</span>
                  <span className="font-medium text-sm">{agent.name}</span>
                  {isSupervisor && (
                    <Badge variant="outline" className="text-xs bg-blue-500/10 text-blue-600 border-blue-500/20">
                      Required
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-muted-foreground line-clamp-2">
                  {agent.description}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant="secondary" className="text-xs">
                    {agent.model}
                  </Badge>
                  <StatusBadge status={agent.status} />
                </div>
              </div>
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
