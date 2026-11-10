import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Eye, EyeOff, Lock, AlertCircle, CheckCircle } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const passwordChangeSchema = z.object({
  newPassword: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
    .regex(/[0-9]/, 'Password must contain at least one number')
    .regex(/[^A-Za-z0-9]/, 'Password must contain at least one special character'),
  confirmPassword: z.string()
}).refine((data) => data.newPassword === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});

type PasswordChangeFormValues = z.infer<typeof passwordChangeSchema>;

interface PasswordChangeFormProps {
  userEmail: string;
  onPasswordChange: (newPassword: string) => Promise<void>;
  onCancel: () => void;
  loading?: boolean;
  className?: string;
}

export const PasswordChangeForm: React.FC<PasswordChangeFormProps> = ({
  userEmail,
  onPasswordChange,
  onCancel,
  loading = false,
  className = ""
}) => {
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    watch,
    clearErrors
  } = useForm<PasswordChangeFormValues>({
    resolver: zodResolver(passwordChangeSchema),
    defaultValues: {
      newPassword: "",
      confirmPassword: "",
    },
  });

  const newPassword = watch('newPassword');

  const handlePasswordSubmit = async (data: PasswordChangeFormValues) => {
    try {
      setError(null);
      clearErrors();
      console.log('🔐 Submitting new password for user:', userEmail);
      
      await onPasswordChange(data.newPassword);
    } catch (error: any) {
      console.error('❌ Password change error:', error);
      setError(error.message || 'Failed to update password');
    }
  };

  const getPasswordStrength = (password: string) => {
    let strength = 0;
    const checks = [
      password.length >= 8,
      /[A-Z]/.test(password),
      /[a-z]/.test(password), 
      /[0-9]/.test(password),
      /[^A-Za-z0-9]/.test(password)
    ];
    
    strength = checks.filter(Boolean).length;
    
    if (strength <= 2) return { label: 'Weak', color: 'text-destructive', bgColor: 'bg-destructive/10' };
    if (strength <= 3) return { label: 'Medium', color: 'text-warning', bgColor: 'bg-warning/10' };
    if (strength <= 4) return { label: 'Strong', color: 'text-success', bgColor: 'bg-success/10' };
    return { label: 'Very Strong', color: 'text-success', bgColor: 'bg-success/20' };
  };

  const passwordStrength = getPasswordStrength(newPassword || '');
  const isLoading = loading || isSubmitting;

  return (
    <div className={`w-full max-w-md mx-auto ${className}`}>
      <Card>
        <CardHeader className="text-center">
          <CardTitle className="text-2xl flex items-center justify-center gap-2">
            <Lock className="h-6 w-6" />
            Password Update Required
          </CardTitle>
          <CardDescription>
            Your account requires a new password. Please create a secure password to continue.
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <form onSubmit={handleSubmit(handlePasswordSubmit)} className="space-y-4">
            {/* User Email Display */}
            <div>
              <Label className="text-sm font-medium text-muted-foreground">Account</Label>
              <div className="mt-1 p-2 bg-surface-2 rounded border text-sm">
                {userEmail}
              </div>
            </div>

            {/* New Password Field */}
            <div>
              <Label htmlFor="newPassword">New Password</Label>
              <div className="relative mt-1">
                <Input
                  id="newPassword"
                  type={showNewPassword ? "text" : "password"}
                  placeholder="Enter your new password"
                  disabled={isLoading}
                  {...register("newPassword")}
                  className={errors.newPassword ? "border-destructive/40" : ""}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 py-2"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                >
                  {showNewPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </Button>
              </div>
              {errors.newPassword && (
                <p className="text-destructive text-xs mt-1">{errors.newPassword.message}</p>
              )}
              
              {/* Password Strength Indicator */}
              {newPassword && (
                <div className="mt-2">
                  <div className="flex items-center justify-between text-xs">
                    <span>Password Strength:</span>
                    <span className={passwordStrength.color}>{passwordStrength.label}</span>
                  </div>
                  <div className="w-full bg-surface-3 rounded-full h-1 mt-1">
                    <div 
                      className={`h-1 rounded-full transition-all ${passwordStrength.bgColor}`}
                      style={{ width: `${(passwordStrength.label === 'Weak' ? 20 : 
                                       passwordStrength.label === 'Medium' ? 50 : 
                                       passwordStrength.label === 'Strong' ? 80 : 100)}%` }}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Confirm Password Field */}
            <div>
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <div className="relative mt-1">
                <Input
                  id="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  placeholder="Confirm your new password"
                  disabled={isLoading}
                  {...register("confirmPassword")}
                  className={errors.confirmPassword ? "border-destructive/40" : ""}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 py-2"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </Button>
              </div>
              {errors.confirmPassword && (
                <p className="text-destructive text-xs mt-1">{errors.confirmPassword.message}</p>
              )}
            </div>

            {/* Password Requirements */}
            <Alert>
              <CheckCircle className="h-4 w-4" />
              <AlertDescription>
                <div className="text-sm">
                  <p className="font-medium mb-2">Password Requirements:</p>
                  <ul className="space-y-1 text-xs">
                    <li className={newPassword?.length >= 8 ? 'text-success' : 'text-muted-foreground'}>
                      • At least 8 characters
                    </li>
                    <li className={/[A-Z]/.test(newPassword || '') ? 'text-success' : 'text-muted-foreground'}>
                      • One uppercase letter
                    </li>
                    <li className={/[a-z]/.test(newPassword || '') ? 'text-success' : 'text-muted-foreground'}>
                      • One lowercase letter
                    </li>
                    <li className={/[0-9]/.test(newPassword || '') ? 'text-success' : 'text-muted-foreground'}>
                      • One number
                    </li>
                    <li className={/[^A-Za-z0-9]/.test(newPassword || '') ? 'text-success' : 'text-muted-foreground'}>
                      • One special character (!@#$%^&*)
                    </li>
                  </ul>
                </div>
              </AlertDescription>
            </Alert>

            {/* Action Buttons */}
            <div className="flex gap-3 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={onCancel}
                disabled={isLoading}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isLoading}
                className="flex-1"
              >
                {isLoading ? "Updating..." : "Update Password"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default PasswordChangeForm;
