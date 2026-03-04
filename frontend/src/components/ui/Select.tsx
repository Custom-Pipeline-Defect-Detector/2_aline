import { useState, useRef, useEffect, ReactNode, Children, cloneElement, isValidElement } from 'react';

interface SelectProps {
  children: ReactNode;
  value?: string;
  onValueChange?: (value: string) => void;
  defaultValue?: string;
}

interface SelectTriggerProps {
  children: ReactNode;
  className?: string;
}

interface SelectContentProps {
  children: ReactNode;
}

interface SelectItemProps {
  children: ReactNode;
  value: string;
}

const Select = ({ children, value, onValueChange, defaultValue }: SelectProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedValue, setSelectedValue] = useState(value || defaultValue || '');
  const selectRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (value !== undefined) {
      setSelectedValue(value);
    }
  }, [value]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (selectRef.current && !selectRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (value: string) => {
    setSelectedValue(value);
    if (onValueChange) {
      onValueChange(value);
    }
    setIsOpen(false);
  };

  const displayValue = Children.toArray(children)
    .find((child) => isValidElement(child) && child.props?.value === selectedValue)
    //@ts-ignore
    ?.props.children;

  return (
    <div ref={selectRef} className="relative">
      <button
        type="button"
        className="flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 [&>span]:line-clamp-1"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span>{displayValue || selectedValue || 'Select...'}</span>
        <svg
          className="h-4 w-4 opacity-50"
          fill="none"
          height="24"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
          viewBox="0 0 24 24"
          width="24"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>
      
      {isOpen && (
        <div className="absolute z-50 mt-1 w-full rounded-md border bg-popover p-1 text-popover-foreground shadow-md">
          {Children.map(children, (child) => {
            if (isValidElement(child)) {
              return cloneElement(child as any, {
                onSelect: handleSelect,
                isSelected: (child as any).props.value === selectedValue
              });
            }
            return child;
          })}
        </div>
      )}
    </div>
  );
};

const SelectTrigger = ({ children, className }: SelectTriggerProps) => {
  return <div className={className}>{children}</div>;
};

const SelectContent = ({ children }: SelectContentProps) => {
  return <div>{children}</div>;
};

const SelectItem = ({ children, value, onSelect, isSelected }: SelectItemProps & { onSelect?: (value: string) => void; isSelected?: boolean }) => {
  return (
    <button
      type="button"
      className={`relative flex w-full cursor-default select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-sm outline-none focus:bg-accent focus:text-accent-foreground ${
        isSelected ? 'bg-accent text-accent-foreground' : 'hover:bg-accent hover:text-accent-foreground'
      }`}
      onClick={() => onSelect && onSelect(value)}
    >
      {children}
    </button>
  );
};

const SelectValue = ({ placeholder }: { placeholder?: string }) => {
  return <>{placeholder}</>;
};

Select.Trigger = SelectTrigger;
Select.Content = SelectContent;
Select.Item = SelectItem;
Select.Value = SelectValue;

export { Select, SelectTrigger, SelectContent, SelectItem, SelectValue };
