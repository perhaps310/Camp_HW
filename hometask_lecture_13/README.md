# Data Engineering Home Task 13

## 1. Data Cleaning Strategy
The raw data contained multiple intentional issues. Here is how and why they were addressed:
* **Missing Primary Keys (`customer_id`, `order_id`, `product_id`):** Dropped. A record without a primary key cannot be referenced and breaks entity integrity.
* **Duplicate Primary Keys:** Dropped duplicates, keeping the last occurrence to ensure uniqueness for database insertion.
* **Invalid/Missing Emails:** Used Regex to identify invalid emails and replaced them with a placeholder (`unknown_{customer_id}@placeholder.com`). We keep the record because the customer's purchase history is still valuable for financial metrics.
* **Negative/Zero Prices:** Replaced with the median price of valid products. Missing prices skew revenue analytics.
* **Negative Quantities:** Converted to absolute values (`abs()`), assuming it was a typo (e.g., `-2` instead of `2`). Zeroes were replaced with `1`.
* **Invalid Timestamps:** Coerced to `NaT` and filled with a default epoch date (`1970-01-01`) to maintain column data type consistency.
* **Mixed-case/Unknown Statuses:** Lowercased and stripped whitespace. Values outside the standard list were mapped to `unknown`.
* **Missing References (Referential Integrity):** Filtered `orders` to include only existing `customer_id`s, and `order_items` to include only existing `order_id`s and `product_id`s. This prevents foreign key constraints violations.

## 2. Output Tables
The pipeline loads cleaned data into staging tables (`stg_customers`, `stg_products`, `stg_orders`, `stg_order_items`) and generates two analytical tables using SQL:
1. **`analytics_customer_ltv` (Customer Lifetime Value):** Calculates total orders, total amount spent, and first/last order dates per customer.
2. **`analytics_monthly_sales`:** Aggregates total quantity sold and total revenue per product on a monthly basis.
