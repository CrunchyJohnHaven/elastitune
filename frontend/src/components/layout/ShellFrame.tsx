import React from 'react';

interface ShellFrameProps {
  children: React.ReactNode;
}

export default function ShellFrame({ children }: ShellFrameProps) {
  return (
    <div
      style={{
        width: '100vw',
        height: '100vh',
        overflow: 'hidden',
        background: '#05070B',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {children}
    </div>
  );
}
