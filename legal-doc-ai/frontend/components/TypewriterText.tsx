import useTypewriter from '../src/hooks/useTypewriter';

type Props = {
  text: string;
  className?: string;
  enabled?: boolean;
  speed?: number;
  startDelay?: number;
};

export default function TypewriterText({
  text,
  className = '',
  enabled = true,
  speed = 14,
  startDelay = 120,
}: Props) {
  const { displayText, isTyping } = useTypewriter(text, {
    enabled,
    speed,
    startDelay,
  });

  return (
    <p className={`${className} ${isTyping ? 'typewriter-active' : ''}`.trim()}>
      {displayText}
    </p>
  );
}
