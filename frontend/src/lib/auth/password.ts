/** Mirrors the Cognito password policy configured in Terraform (min 8, upper, lower, number). */
export function passwordProblem(pw: string): string | null {
  if (pw.length < 8) return 'Use at least 8 characters.';
  if (!/[a-z]/.test(pw) || !/[A-Z]/.test(pw) || !/\d/.test(pw))
    return 'Include upper and lower case letters and a number.';
  return null;
}
