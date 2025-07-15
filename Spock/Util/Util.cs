namespace Spock.Util;

public static class Util
{
    public static bool NullableSequenceEqual<T>(this IEnumerable<T>? first, IEnumerable<T>? second)
    {
        if (first == null && second == null) return true;
        if (first == null || second == null) return false;
        return first.SequenceEqual(second);
    }
}