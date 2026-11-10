import type { Config } from "tailwindcss";

/**
 * Tailwind is wired to the design tokens in src/styles/tokens.css.
 * Add colours there first, then expose them here. Never add raw hex values.
 */
const token = (name: string) => `hsl(var(--${name}))`;

export default {
	darkMode: ["class"],
	content: [
		"./pages/**/*.{ts,tsx}",
		"./components/**/*.{ts,tsx}",
		"./app/**/*.{ts,tsx}",
		"./src/**/*.{ts,tsx}",
	],
	prefix: "",
	theme: {
		container: {
			center: true,
			padding: '2rem',
			screens: {
				'2xl': '1400px'
			}
		},
		extend: {
			fontFamily: {
				sans: ['var(--font-sans)'],
				mono: ['var(--font-mono)'],
			},
			fontSize: {
				// App type scale. 12px is the smallest size allowed in the product.
				'2xs': ['0.75rem', { lineHeight: '1rem' }],
				xs: ['0.75rem', { lineHeight: '1rem' }],
				sm: ['0.8125rem', { lineHeight: '1.25rem' }],
				base: ['0.875rem', { lineHeight: '1.375rem' }],
				md: ['0.9375rem', { lineHeight: '1.5rem' }],
				lg: ['1.0625rem', { lineHeight: '1.5rem', letterSpacing: '-0.01em' }],
				xl: ['1.25rem', { lineHeight: '1.75rem', letterSpacing: '-0.02em' }],
				'2xl': ['1.5rem', { lineHeight: '2rem', letterSpacing: '-0.025em' }],
				'3xl': ['1.875rem', { lineHeight: '2.25rem', letterSpacing: '-0.03em' }],
				'4xl': ['2.375rem', { lineHeight: '2.625rem', letterSpacing: '-0.035em' }],
			},
			borderRadius: {
				xl: 'calc(var(--radius) + 4px)',
				lg: 'var(--radius)',
				md: 'calc(var(--radius) - 2px)',
				sm: 'calc(var(--radius) - 4px)'
			},
			colors: {
				border: token('border'),
				'border-strong': token('border-strong'),
				input: token('input'),
				ring: token('ring'),
				background: token('background'),
				foreground: token('foreground'),
				'subtle-foreground': token('subtle-foreground'),
				surface: {
					2: token('surface-2'),
					3: token('surface-3'),
				},
				primary: {
					DEFAULT: token('primary'),
					foreground: token('primary-foreground')
				},
				brand: {
					DEFAULT: token('brand'),
					hi: token('brand-hi'),
					lo: token('brand-lo'),
				},
				secondary: {
					DEFAULT: token('secondary'),
					foreground: token('secondary-foreground')
				},
				destructive: {
					DEFAULT: token('destructive'),
					foreground: token('destructive-foreground')
				},
				success: {
					DEFAULT: token('success'),
					foreground: token('success-foreground')
				},
				warning: {
					DEFAULT: token('warning'),
					foreground: token('warning-foreground')
				},
				info: {
					DEFAULT: token('info'),
					foreground: token('info-foreground')
				},
				muted: {
					DEFAULT: token('muted'),
					foreground: token('muted-foreground')
				},
				accent: {
					DEFAULT: token('accent'),
					foreground: token('accent-foreground')
				},
				popover: {
					DEFAULT: token('popover'),
					foreground: token('popover-foreground')
				},
				card: {
					DEFAULT: token('card'),
					foreground: token('card-foreground')
				},
				chart: {
					1: token('chart-1'),
					2: token('chart-2'),
					3: token('chart-3'),
					4: token('chart-4'),
					5: token('chart-5'),
					6: token('chart-6'),
				},
				sidebar: {
					DEFAULT: token('sidebar'),
					foreground: token('sidebar-fg'),
					primary: 'hsl(var(--sidebar-primary, var(--primary)))',
					'primary-foreground': 'hsl(var(--sidebar-primary-foreground, var(--primary-foreground)))',
					accent: 'hsl(var(--sidebar-accent, var(--accent)))',
					'accent-foreground': 'hsl(var(--sidebar-accent-foreground, var(--accent-foreground)))',
					border: token('sidebar-border'),
					ring: 'hsl(var(--sidebar-ring, var(--ring)))'
				},
				header: {
					DEFAULT: token('header'),
				},
				map: {
					water: '#1A3A54',
					land: '#252A33'
				}
			},
			boxShadow: {
				xs: 'var(--shadow-xs)',
				sm: 'var(--shadow-sm)',
				md: 'var(--shadow-md)',
				lg: 'var(--shadow-lg)',
			},
			transitionTimingFunction: {
				brand: 'var(--ease)',
				'brand-out': 'var(--ease-out)',
			},
			transitionDuration: {
				fast: '120ms',
				DEFAULT: '200ms',
				slow: '420ms',
			},
			keyframes: {
				'accordion-down': {
					from: { height: '0' },
					to: { height: 'var(--radix-accordion-content-height)' }
				},
				'accordion-up': {
					from: { height: 'var(--radix-accordion-content-height)' },
					to: { height: '0' }
				}
			},
			animation: {
				'accordion-down': 'accordion-down 0.2s ease-out',
				'accordion-up': 'accordion-up 0.2s ease-out',
				'fade-in': 'fade-in var(--dur) var(--ease) both',
				'fade-up': 'fade-up var(--dur-slow) var(--ease-out) both',
				'scale-in': 'scale-in var(--dur) var(--ease-out) both',
				'slide-in-right': 'slide-in-right var(--dur-slow) var(--ease-out) both',
				'float-y': 'float-y 5s ease-in-out infinite',
			}
		}
	},
	plugins: [require("tailwindcss-animate")],
} satisfies Config;
