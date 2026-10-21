using System.Globalization;
using System.Text.RegularExpressions;

namespace Ennichi.Editor
{
    // Version eligibility only; this does not certify Unity or platform compatibility.
    public static class UnityVersionPolicy
    {
        public const string MinimumVersion = "6000.0.65f1";
        public const string Requirement = "Unity 6000 final releases (f), " + MinimumVersion + " or later";

        public static bool IsSupported(string version)
        {
            if (string.IsNullOrEmpty(version)) return false;
            var match = Regex.Match(version, @"\A6000\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)f([1-9][0-9]*)\z");
            int minor, patch, revision;
            if (!match.Success
                || !int.TryParse(match.Groups[1].Value, NumberStyles.None, CultureInfo.InvariantCulture, out minor)
                || !int.TryParse(match.Groups[2].Value, NumberStyles.None, CultureInfo.InvariantCulture, out patch)
                || !int.TryParse(match.Groups[3].Value, NumberStyles.None, CultureInfo.InvariantCulture, out revision))
                return false;

            // Compare numeric release components: 6000.1.0f1 is later than 6000.0.65f1.
            return minor > 0 || patch >= 65;
        }
    }
}
