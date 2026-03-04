import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className = '', ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={[
          'w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 shadow-sm',
          'transition',
          'placeholder:text-slate-400',
          'focus:border-emerald-300/60 focus:outline-none focus:ring-2 focus:ring-emerald-400/30',
          'disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500',
          className,
        ].join(' ')}
        {...props}
      />
    )
  }
);

Input.displayName = "Input";

export default Input;
