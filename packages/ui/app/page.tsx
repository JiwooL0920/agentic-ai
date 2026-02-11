'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Sparkles, ArrowRight, Zap, Shield, Brain } from 'lucide-react';

interface Blueprint {
  slug: string;
  name: string;
  description: string;
  agent_count: number;
  icon?: string;
}

const defaultBlueprints: Blueprint[] = [
  {
    slug: 'devassist',
    name: 'DevAssist',
    description: 'Full-stack development assistant with expertise in Kubernetes, Terraform, Python, React, and system architecture',
    agent_count: 5,
    icon: '💻',
  },
];

const features = [
  { 
    icon: (props: any) => <Brain {...props} suppressHydrationWarning />, 
    title: 'Multi-Agent', 
    desc: 'Specialized AI agents for every task' 
  },
  { 
    icon: (props: any) => <Zap {...props} suppressHydrationWarning />, 
    title: 'Real-time', 
    desc: 'Streaming responses with live updates' 
  },
  { 
    icon: (props: any) => <Shield {...props} suppressHydrationWarning />, 
    title: 'Local-first', 
    desc: 'Powered by Ollama, runs on your hardware' 
  },
];

export default function Home() {
  const [blueprints, setBlueprints] = useState<Blueprint[]>([]);
  const [loading, setLoading] = useState(true);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    async function fetchBlueprints() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/blueprints`);
        if (response.ok) {
          const data = await response.json();
          const detailed = await Promise.all(
            data.map(async (slug: string) => {
              const res = await fetch(`${apiUrl}/api/blueprints/${slug}`);
              if (res.ok) return res.json();
              return null;
            })
          );
          const validBlueprints = detailed.filter(Boolean);
          setBlueprints(validBlueprints.length > 0 ? validBlueprints : defaultBlueprints);
        } else {
          setBlueprints(defaultBlueprints);
        }
      } catch {
        setBlueprints(defaultBlueprints);
      } finally {
        setLoading(false);
      }
    }
    fetchBlueprints();
  }, []);

  return (
    <div className="min-h-screen relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-purple-500/5" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-gradient-to-b from-primary/10 to-transparent rounded-full blur-3xl opacity-50" />
      
      <div className="relative z-10 max-w-5xl mx-auto px-6 py-16">
        <div className="text-center mb-16 space-y-6">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium mb-4">
            <Sparkles className="w-4 h-4" />
            <span>Multi-Agent AI Platform</span>
          </div>
          
          <h1 className="text-5xl md:text-6xl font-bold tracking-tight">
            <span className="gradient-text">Agentic AI</span>
          </h1>
          
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            Harness the power of specialized AI agents. Each blueprint combines multiple experts
            to tackle complex tasks with precision.
          </p>
        </div>

        {mounted && (
          <div className="grid md:grid-cols-3 gap-6 mb-16">
            {features.map((f, i) => (
              <div 
                key={f.title}
                className="flex flex-col items-center text-center p-6 rounded-2xl bg-card/50 border border-border/50 backdrop-blur-sm"
                style={{ animationDelay: `${i * 100}ms` }}
              >
                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
                  <f.icon className="w-6 h-6 text-primary" />
                </div>
                <h3 className="font-semibold mb-1">{f.title}</h3>
                <p className="text-sm text-muted-foreground">{f.desc}</p>
              </div>
            ))}
          </div>
        )}

        <div className="mb-8">
          <h2 className="text-2xl font-semibold mb-2">Choose a Blueprint</h2>
          <p className="text-muted-foreground">Select an AI team to start your conversation</p>
        </div>

        {loading ? (
          <div className="grid md:grid-cols-2 gap-6">
            {[1, 2].map((i) => (
              <div key={i} className="h-48 rounded-2xl animate-shimmer" />
            ))}
          </div>
        ) : blueprints.length === 0 ? (
          <div className="text-center py-16 text-muted-foreground">
            <p>No blueprints available</p>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-6">
            {blueprints.map((bp) => (
              <Link key={bp.slug} href={`/${bp.slug}`}>
                <Card className="h-full card-hover cursor-pointer group relative overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                  <CardHeader className="relative p-6">
                    <div className="flex items-start gap-4">
                      <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/20 to-purple-500/20 flex items-center justify-center text-4xl shadow-lg shadow-primary/10 group-hover:scale-110 transition-transform">
                        {bp.icon || '🤖'}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <CardTitle className="text-xl group-hover:text-primary transition-colors">
                            {bp.name}
                          </CardTitle>
                          <ArrowRight className="w-4 h-4 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all text-primary" />
                        </div>
                        <CardDescription className="text-sm leading-relaxed mb-4">
                          {bp.description}
                        </CardDescription>
                        <div className="flex items-center gap-3">
                          <Badge variant="secondary" className="bg-primary/10 text-primary border-0">
                            {bp.agent_count} agents
                          </Badge>
                          <Badge variant="outline" className="text-muted-foreground">
                            Ready
                          </Badge>
                        </div>
                      </div>
                    </div>
                  </CardHeader>
                </Card>
              </Link>
            ))}
          </div>
        )}

        <footer className="mt-20 pt-8 border-t border-border/50 text-center">
          <p className="text-sm text-muted-foreground">
            Powered by <span className="font-medium text-foreground">Ollama</span> + <span className="font-medium text-foreground">agent-squad</span>
          </p>
        </footer>
      </div>
    </div>
  );
}
