'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface Blueprint {
  slug: string;
  name: string;
  description: string;
  agent_count: number;
  icon?: string;
}

// Default blueprints (used when API is not available)
const defaultBlueprints: Blueprint[] = [
  {
    slug: 'devassist',
    name: 'DevAssist',
    description: 'Full-stack development assistant',
    agent_count: 5,
    icon: '💻',
  },
];

export default function Home() {
  const [blueprints, setBlueprints] = useState<Blueprint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchBlueprints() {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
        const response = await fetch(`${apiUrl}/api/blueprints`);
        if (response.ok) {
          const data = await response.json();
          // Fetch details for each blueprint
          const detailed = await Promise.all(
            data.map(async (slug: string) => {
              const res = await fetch(`${apiUrl}/api/blueprints/${slug}`);
              if (res.ok) return res.json();
              return null;
            })
          );
          const validBlueprints = detailed.filter(Boolean);
          if (validBlueprints.length > 0) {
            setBlueprints(validBlueprints);
          } else {
            // Fall back to defaults if API returns empty
            setBlueprints(defaultBlueprints);
          }
        } else {
          // Fall back to defaults if API fails
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
    <div className="min-h-screen p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2">Agentic AI</h1>
          <p className="text-muted-foreground">
            Select a blueprint to start chatting with specialized AI agents
          </p>
        </div>

        {/* Blueprint Grid */}
        {loading ? (
          <div className="text-center py-8">Loading blueprints...</div>
        ) : blueprints.length === 0 ? (
          <div className="text-center py-8">No blueprints available</div>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            {blueprints.map((bp) => (
            <Link key={bp.slug} href={`/${bp.slug}`}>
              <Card className="h-full hover:border-primary transition-colors cursor-pointer group">
                <CardHeader>
                  <div className="flex items-start gap-4">
                    <span className="text-4xl">{bp.icon || '🤖'}</span>
                    <div className="flex-1">
                      <CardTitle className="group-hover:text-primary transition-colors">
                        {bp.name}
                      </CardTitle>
                      <CardDescription className="mt-1">
                        {bp.description}
                      </CardDescription>
                      <div className="mt-3">
                        <Badge variant="secondary">
                          {bp.agent_count} agents
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

        {/* Footer */}
        <div className="mt-12 text-center text-sm text-muted-foreground">
          <p>Powered by Ollama + agent-squad</p>
        </div>
      </div>
    </div>
  );
}
