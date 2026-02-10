'use client';

import { useState, useEffect, useCallback } from 'react';
import { Cpu, MemoryStick, HardDrive, Zap } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

interface ResourceUsage {
  name: string;
  percent: number;
  used: string | null;
  total: string | null;
}

interface SystemStatsData {
  cpu: ResourceUsage;
  memory: ResourceUsage;
  gpu: ResourceUsage;
  storage: ResourceUsage;
  timestamp: number;
}

function getColorClass(percent: number): string {
  if (percent < 50) return 'text-green-500';
  if (percent < 75) return 'text-yellow-500';
  if (percent < 90) return 'text-orange-500';
  return 'text-red-500';
}

function getBarColor(percent: number): string {
  if (percent < 50) return 'bg-green-500';
  if (percent < 75) return 'bg-yellow-500';
  if (percent < 90) return 'bg-orange-500';
  return 'bg-red-500';
}

interface StatItemProps {
  icon: React.ReactNode;
  label: string;
  percent: number;
  used?: string | null;
  total?: string | null;
}

function StatItem({ icon, label, percent, used, total }: StatItemProps) {
  const displayPercent = Math.round(percent);
  const details = used && total ? `${used} / ${total}` : null;

  return (
    <TooltipProvider delayDuration={0}>
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-md hover:bg-muted/50 transition-colors cursor-default">
            <span className={getColorClass(percent)}>{icon}</span>
            <div className="flex flex-col min-w-[3rem]">
              <span className={`text-xs font-medium tabular-nums ${getColorClass(percent)}`}>
                {displayPercent}%
              </span>
              <div className="w-full h-1 bg-muted rounded-full overflow-hidden">
                <div
                  className={`h-full ${getBarColor(percent)} transition-all duration-500`}
                  style={{ width: `${Math.min(percent, 100)}%` }}
                />
              </div>
            </div>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="text-xs">
          <p className="font-medium">{label}: {displayPercent}%</p>
          {details && <p className="text-muted-foreground">{details}</p>}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

interface MacGpuMetrics {
  percent: number;
  vram_used_gb: number;
  vram_allocated_gb: number;
}

export function SystemStats() {
  const [stats, setStats] = useState<SystemStatsData | null>(null);
  const [gpuMetrics, setGpuMetrics] = useState<MacGpuMetrics | null>(null);
  const [error, setError] = useState(false);

  const fetchStats = useCallback(async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
      const response = await fetch(`${apiUrl}/health/stats`);
      if (!response.ok) throw new Error('Failed to fetch stats');
      const data = await response.json();
      setStats(data);
      setError(false);
    } catch {
      setError(true);
    }
  }, []);

  const fetchGpuMetrics = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8002/gpu');
      if (response.ok) {
        const data = await response.json();
        console.log('[GPU Metrics]', data);
        setGpuMetrics(data);
      }
    } catch (e) {
      console.error('[GPU Metrics] fetch failed:', e);
      setGpuMetrics(null);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchGpuMetrics();
    const interval = setInterval(() => {
      fetchStats();
      fetchGpuMetrics();
    }, 2000);
    return () => clearInterval(interval);
  }, [fetchStats, fetchGpuMetrics]);

  if (error || !stats) {
    return (
      <div className="flex items-center gap-1 text-xs text-muted-foreground">
        <span className="animate-pulse">Loading stats...</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-0.5 border border-border/50 rounded-lg bg-card/50 backdrop-blur-sm">
      <StatItem
        icon={<Cpu className="w-3.5 h-3.5" />}
        label="CPU"
        percent={stats.cpu.percent}
      />
      <div className="w-px h-4 bg-border/50" />
      <StatItem
        icon={<MemoryStick className="w-3.5 h-3.5" />}
        label="Memory"
        percent={stats.memory.percent}
        used={stats.memory.used}
        total={stats.memory.total}
      />
      <div className="w-px h-4 bg-border/50" />
      <StatItem
        icon={<Zap className="w-3.5 h-3.5" />}
        label="GPU"
        percent={gpuMetrics?.percent ?? stats.gpu.percent}
        used={gpuMetrics ? `${gpuMetrics.vram_used_gb.toFixed(1)}GB` : stats.gpu.used}
        total={gpuMetrics ? `${gpuMetrics.vram_allocated_gb.toFixed(1)}GB` : stats.gpu.total}
      />
      <div className="w-px h-4 bg-border/50" />
      <StatItem
        icon={<HardDrive className="w-3.5 h-3.5" />}
        label="Storage"
        percent={stats.storage.percent}
        used={stats.storage.used}
        total={stats.storage.total}
      />
    </div>
  );
}
