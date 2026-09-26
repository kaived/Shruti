import React, { forwardRef } from 'react';
import { Loader2 } from 'lucide-react';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'success';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  icon?: React.ReactNode;
  iconRight?: React.ReactNode;
}

const VARIANT_STYLES: Record<ButtonVariant, string> = {
  primary:
    'bg-[#0047ab] hover:bg-[#003785] active:bg-[#002f70] text-white shadow-xs hover:shadow border border-transparent',
  secondary:
    'bg-white hover:bg-slate-50 active:bg-slate-100 text-slate-700 border border-slate-200 hover:border-slate-300 shadow-2xs',
  ghost:
    'bg-transparent hover:bg-slate-100 active:bg-slate-200 text-slate-600 hover:text-slate-900 border border-transparent',
  danger:
    'bg-red-600 hover:bg-red-700 active:bg-red-800 text-white shadow-xs border border-transparent',
  success:
    'bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white shadow-xs border border-transparent',
};

const SIZE_STYLES: Record<ButtonSize, string> = {
  sm: 'h-8 px-3.5 text-xs gap-1.5 rounded-md font-medium',
  md: 'h-9 px-5 text-[13px] gap-2 rounded-md font-semibold',
  lg: 'h-10 px-6 text-sm gap-2.5 rounded-lg font-semibold',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      isLoading = false,
      icon,
      iconRight,
      disabled,
      className = '',
      children,
      type = 'button',
      ...rest
    },
    ref
  ) => {
    const isDisabled = disabled || isLoading;

    return (
      <button
        ref={ref}
        type={type}
        disabled={isDisabled}
        className={`inline-flex items-center justify-center w-fit transition-all duration-150 cursor-pointer select-none leading-none whitespace-nowrap shrink-0 ${
          VARIANT_STYLES[variant]
        } ${SIZE_STYLES[size]} ${
          isDisabled ? 'opacity-60 cursor-not-allowed pointer-events-none' : ''
        } ${className}`}
        {...rest}
      >
        {isLoading ? (
          <Loader2 className="animate-spin shrink-0" size={size === 'sm' ? 14 : 16} />
        ) : (
          icon && <span className="shrink-0 flex items-center">{icon}</span>
        )}
        {children && <span>{children}</span>}
        {!isLoading && iconRight && <span className="shrink-0 flex items-center">{iconRight}</span>}
      </button>
    );
  }
);

Button.displayName = 'Button';
