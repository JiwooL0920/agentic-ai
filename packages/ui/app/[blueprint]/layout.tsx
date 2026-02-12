'use client';

import { Suspense } from 'react';
import { useParams } from 'next/navigation';
import { SessionSidebar } from '@/components/session';

export default function BlueprintLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const blueprint = params.blueprint as string;

  return (
    <div className="flex h-screen">
      <Suspense fallback={<div className="w-72 border-r bg-muted/30" />}>
        <SessionSidebar blueprint={blueprint} />
      </Suspense>
      <div className="flex-1 overflow-hidden">{children}</div>
    </div>
  );
}
