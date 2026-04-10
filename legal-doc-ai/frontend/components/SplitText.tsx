import { useMemo } from 'react';

type Props = {
  text: string;
  className?: string;
  delay?: number;
  duration?: number;
};

export default function SplitText({
  text,
  className = '',
  delay = 70,
  duration = 1,
}: Props) {
  const words = useMemo(() => text.trim().split(/\s+/), [text]);

  return (
    <span className={`split-text ${className}`.trim()} aria-label={text}>
      {words.map((word, index) => (
        <span
          key={`${word}-${index}`}
          className="split-word"
          style={{
            animationDelay: `${index * delay}ms`,
            animationDuration: `${duration}s`,
          }}
        >
          {word}
          {index < words.length - 1 ? '\u00A0' : ''}
        </span>
      ))}
    </span>
  );
}
