# Books to Browse
A demo online bookstore for browsing and purchasing books.

## searchBooks
Search the book catalog by keyword. Matches against title and author.

### Params
- `query` (string, required): Search query text.

### Output
```typescript
Array<{ id: string; title: string; author: string; price: number; rating: number; category: string; inStock: boolean }>
```

### Sample Code
```js
const results = await global.searchBooks(query);
```

## getBookDetails
Get full details for a specific book by its ID.

### Params
- `bookId` (string, required): The unique book identifier.

### Output
```typescript
{ id: string; title: string; author: string; price: number; rating: number; category: string; inStock: boolean; description: string; coverUrl: string }
```

### Sample Code
```js
const book = await global.getBookDetails(bookId);
```

## filterByCategory
Filter books by category name.

### Params
- `category` (string, required): The category to filter by (e.g. "Science Fiction", "Mystery").

### Output
```typescript
Array<{ id: string; title: string; author: string; price: number; rating: number; category: string; inStock: boolean }>
```

### Sample Code
```js
const books = await global.filterByCategory(category);
```

## addToBasket
Add a book to the shopping basket.

### Params
- `bookId` (string, required): The unique book identifier.
- `quantity` (number, optional, default=1): Number of copies to add.

### Output
```typescript
{ success: boolean; basketCount: number; item: { title: string; quantity: number; price: number } }
```

### Sample Code
```js
const result = await global.addToBasket(bookId, quantity);
```

## getBasket
View the current contents of the shopping basket.

### Params

### Output
```typescript
{ items: Array<{ bookId: string; title: string; quantity: number; price: number }>; total: number; itemCount: number }
```

### Sample Code
```js
const basket = await global.getBasket();
```

## removeFromBasket
Remove a book from the shopping basket.

### Params
- `bookId` (string, required): The unique book identifier to remove.

### Output
```typescript
{ success: boolean; basketCount: number }
```

### Sample Code
```js
const result = await global.removeFromBasket(bookId);
```
