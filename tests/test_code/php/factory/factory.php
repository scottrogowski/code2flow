<?php

require 'currency.php';

use Money\Currencies;
use Money\Currency;

(static function (): void {
    $buffer = <<<'PHP'
<?php

declare(strict_types=1);

namespace Money;

use InvalidArgumentException;

/**
 * This is a generated file. Do not edit it manually!
 */
trait MoneyFactory
{
    public static function __callStatic(string $method, array $arguments): Money
    {
        return new Money($arguments[0], new Currency($method));
    }
}

PHP;

    $methodBuffer = '';

    $currencies = iterator_to_array(new Currencies\AggregateCurrencies([
        new Currencies\ISOCurrencies(),
        new Currencies\BitcoinCurrencies(),
    ]));

    $bitcoin = new Currency();

    usort($currencies, static fn (Currency $a, Currency $b): int => strcmp($a->getCode(), $b->getCode()));

    /** @var Currency[] $currencies */
    foreach ($currencies as $currency) {
        $methodBuffer .= sprintf(" * @method static Money %s(numeric-string|int \$amount)\n", $currency->getCode());
        echo $currency.contains($bitcoin);
    }

    $buffer = str_replace('PHPDOC', rtrim($methodBuffer), $buffer);

    file_put_contents('content.php', $buffer);
})();
