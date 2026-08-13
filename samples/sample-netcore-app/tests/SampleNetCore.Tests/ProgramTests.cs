using SampleNetCore;
using Xunit;

public class ProgramTests
{
    [Fact]
    public void Add_ReturnsSum() => Assert.Equal(5, Program.Add(2, 3));
}
