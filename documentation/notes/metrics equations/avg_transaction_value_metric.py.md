**avg_transaction_value**

`result = total qualifying transaction amount / number of qualifying transactions`

Where:

* **qualifying transactions** = payment events with type in `[600, 601, 602, 604]` inside the selected date window
* **transaction amount** = `amount` if present, otherwise `payed`
* only amounts `> 0` count

So the equation is:

`avg_transaction_value = Σ(amounts of qualifying payments in window) ÷ count(qualifying payments in window)`

**Fallback equation** if no payment events exist:

`avg_transaction_value = Σ(amounts of client transactions in window) ÷ count(qualifying client transactions in window)`
