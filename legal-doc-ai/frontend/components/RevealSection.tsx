import { ReactNode } from 'react';
import useScrollReveal from '../src/hooks/useScrollReveal';

type Props = {
  children: ReactNode;
  className?: string;
};

export default function RevealSection({ children, className = '' }: Props) {
  const ref = useScrollReveal<HTMLDivElement>();

  return (
    <div ref={ref} className={`reveal-on-scroll ${className}`.trim()}>
      {children}
    </div>
  );
}
