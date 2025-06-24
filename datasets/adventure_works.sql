
SELECT * FROM Address;	adventure_works
SELECT * FROM Product;	adventure_works
SELECT Name FROM ProductCategory;	adventure_works
SELECT DISTINCT Color FROM Product;	adventure_works
SELECT Name, ListPrice FROM Product;	adventure_works
SELECT * FROM SalesOrderDetail;	adventure_works
SELECT DISTINCT AddressType FROM CustomerAddress;	adventure_works
SELECT DISTINCT ShipMethod FROM SalesOrderHeader;	adventure_works
SELECT AVG(Weight) FROM Product;	adventure_works
SELECT P.ProductID, P.Name, SUM(SD.OrderQty) FROM Product as P JOIN SalesOrderDetail as SD ON P.ProductID = SD.ProductID GROUP BY P.ProductID HAVING SUM(SD.OrderQty) < 500 ORDER BY SUM(SD.OrderQty) ASC;	adventure_works
SELECT Product.Name FROM PRODUCT WHERE SellEndDate IS NOT NULL AND julianday(SellEndDate) - julianday(SellStartDate) = 10;	adventure_works
