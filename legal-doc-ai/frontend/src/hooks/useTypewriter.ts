import { useEffect, useMemo, useState } from 'react';

type Options = {
  enabled?: boolean;
  speed?: number;
  startDelay?: number;
};

export default function useTypewriter(text: string, options: Options = {}) {
  const { enabled = true, speed = 14, startDelay = 120 } = options;
  const [displayText, setDisplayText] = useState(enabled ? '' : text);
  const [isTyping, setIsTyping] = useState(false);

  const normalizedText = useMemo(() => text ?? '', [text]);

  useEffect(() => {
    if (!enabled || !normalizedText) {
      setDisplayText(normalizedText);
      setIsTyping(false);
      return;
    }

    let timeoutId: ReturnType<typeof setTimeout>;
    let index = 0;

    setDisplayText('');
    setIsTyping(true);

    const step = () => {
      index += 1;
      setDisplayText(normalizedText.slice(0, index));
      if (index < normalizedText.length) {
        timeoutId = setTimeout(step, speed);
      } else {
        setIsTyping(false);
      }
    };

    timeoutId = setTimeout(step, startDelay);

    return () => clearTimeout(timeoutId);
  }, [normalizedText, enabled, speed, startDelay]);

  return { displayText, isTyping };
}
