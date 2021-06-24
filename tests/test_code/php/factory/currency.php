<?php

declare(strict_types=1);

namespace Money;

/**
 * Currency Value Object.
 *
 * Holds Currency specific data.
 *
 * @psalm-immutable
 */
final class Currency implements JsonSerializable
{
    /**
     * Currency code.
     *
     * @psalm-var non-empty-string
     */
    private string $code;

    /** @psalm-param non-empty-string $code */
    public function __construct(string $code)
    {
        /** @psalm-var non-empty-string $this->code */
        $this->code = strtoupper($code);
    }

    /**
     * Returns the currency code.
     *
     * @psalm-return non-empty-string
     */
    public function getCode(): string
    {
        return $this->code;
    }

    /**
     * Checks whether this currency is the same as an other.
     */
    public function equals(Currency $other): bool
    {
        return $this->code === $other->code;
    }

    public function __toString(): string
    {
        return $this->code;
    }

    /**
     * {@inheritdoc}
     *
     * @return string
     */
    public function jsonSerialize()
    {
        return $this->code;
    }
}


/**
 * Implement this to provide a list of currencies.
 */
interface Currencies extends IteratorAggregate
{
    /**
     * Checks whether a currency is available in the current context.
     */
    public function contains(Currency $currency): bool;

    /**
     * Returns the subunit for a currency.
     *
     * @throws UnknownCurrencyException If currency is not available in the current context.
     */
    public function subunitFor(Currency $currency): int;

    /**
     * @psalm-return Traversable<int|string, Currency>
     */
    public function getIterator(): Traversable;
}
