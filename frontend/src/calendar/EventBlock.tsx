// One stripe per calendar an event is in
export function Stripes({ colors }: { colors: string[] }) {
    return (
        <span className="flex h-full shrink-0">
            {colors.map((color, i) => (
                <span key={i} data-testid="stripe" className="block h-full w-1.5" style={{ backgroundColor: color }} />
            ))}
        </span>
    );
}
