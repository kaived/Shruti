import React, { forwardRef } from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  icon?: React.ReactNode;
  iconRight?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, icon, iconRight, className = '', id, disabled, ...rest }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

    return (
      <div className="flex flex-col gap-1.5 w-full">
        {label && (
          <label htmlFor={inputId} className="text-xs font-semibold text-slate-700 select-none">
            {label}
            {rest.required && <span className="text-red-500 ml-0.5">*</span>}
          </label>
        )}
        <div className="relative flex items-center w-full">
          {icon && (
            <div className="absolute left-3 flex items-center pointer-events-none text-slate-400">
              {icon}
            </div>
          )}
          <input
            ref={ref}
            id={inputId}
            disabled={disabled}
            className={`w-full text-sm bg-white border rounded-lg transition-colors outline-none ${
              icon ? 'pl-9' : 'pl-3.5'
            } ${iconRight ? 'pr-9' : 'pr-3.5'} py-2 ${
              error
                ? 'border-red-400 focus:border-red-500 focus:ring-2 focus:ring-red-500/20 text-red-900'
                : 'border-slate-200 hover:border-slate-300 focus:border-[#0047ab] focus:ring-2 focus:ring-[#0047ab]/20 text-slate-900'
            } ${disabled ? 'bg-slate-50 text-slate-400 cursor-not-allowed' : ''} ${className}`}
            {...rest}
          />
          {iconRight && (
            <div className="absolute right-3 flex items-center pointer-events-none text-slate-400">
              {iconRight}
            </div>
          )}
        </div>
        {error ? (
          <p className="text-xs text-red-600 font-medium">{error}</p>
        ) : helperText ? (
          <p className="text-xs text-slate-500">{helperText}</p>
        ) : null}
      </div>
    );
  }
);

Input.displayName = 'Input';
