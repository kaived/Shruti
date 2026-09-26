import React from 'react';

export interface FormFieldProps {
  label?: string;
  badge?: string;
  required?: boolean;
  error?: string;
  helperText?: string;
  children: React.ReactNode;
  className?: string;
}

export function FormField({
  label,
  badge,
  required,
  error,
  helperText,
  children,
  className = '',
}: FormFieldProps) {
  return (
    <div className={`flex flex-col gap-1.5 w-full ${className}`}>
      {(label || badge) && (
        <div className="flex items-center justify-between">
          {label && (
            <label className="text-xs font-semibold text-slate-700 select-none">
              {label}
              {required && <span className="text-red-500 ml-0.5">*</span>}
            </label>
          )}
          {badge && (
            <span className="text-[10px] font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
              {badge}
            </span>
          )}
        </div>
      )}
      {children}
      {error ? (
        <p className="text-xs text-red-600 font-medium">{error}</p>
      ) : helperText ? (
        <p className="text-xs text-slate-500">{helperText}</p>
      ) : null}
    </div>
  );
}
