
SELECT * FROM Address
SELECT * FROM Product	
SELECT Name FROM ProductCategory
SELECT DISTINCT Color FROM Product
SELECT Name, ListPrice FROM Product
SELECT * FROM SalesOrderDetail
SELECT DISTINCT AddressType FROM CustomerAddress
SELECT DISTINCT ShipMethod FROM SalesOrderHeader
SELECT AVG(Weight) FROM Product
SELECT P.ProductID, P.Name, SUM(SD.OrderQty) FROM Product AS P JOIN SalesOrderDetail AS SD ON P.ProductID = SD.ProductID GROUP BY P.ProductID 
SELECT Product.Name FROM PRODUCT WHERE SellEndDate IS NOT NULL AND julianday(SellEndDate) - julianday(SellStartDate) = 10
