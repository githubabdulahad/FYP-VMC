import clsx from 'clsx';
import type { HTMLAttributes } from 'react';

export function Card({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={clsx('glass-panel rounded-2xl p-5 shadow-xl', className)} {...props}>
      {children}
    </div>
  );
}
