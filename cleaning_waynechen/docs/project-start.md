# Project Starting Point

## Selected project area

Amazon Product-Listing Quality, focusing on the Appliances category.

## Why our team is interested in it

Our team is interested in understanding how customer reviews can reveal important product information that is missing or unclear in appliance listings. This project also allows us to explore how better product information could improve customers’ shopping experiences and help AI shopping tools make more accurate comparisons.

## Candidate Vision A

An Amazon Appliances category manager must decide which product listings should be updated first because customers repeatedly mention important information that is missing or unclear in those listings.

## Candidate Vision B

An Amazon shopping-experience product manager must decide which product details should be required and displayed consistently across appliance listings so customers and AI shopping tools can compare products accurately.

## Core data source we confirmed we can access

McAuley Lab’s Amazon Reviews 2023 dataset:
https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023

We confirmed that the dataset page and its documentation are accessible and that separate user-review and product-metadata files are available for the Appliances category. The documentation reports approximately 2.1 million appliance reviews covering approximately 94,300 products.

Review records include ratings, review titles and text, timestamps, helpfulness votes, verified-purchase status, and product identifiers. Product metadata includes product titles, features, descriptions, prices, categories, product details, and product identifiers.

## Three questions we still need to resolve

1. Should we analyze the entire Appliances category or narrow the scope to particular appliance subcategories?
2. How should we define and validate whether important product information is genuinely missing or unclear in a listing?
3. How complete and reliable is the connection between user reviews and product metadata through the `parent_asin` identifier?