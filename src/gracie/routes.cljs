(ns gracie.routes
  (:require
    [gracie.routes.home :as home]
    [gracie.routes.illustrations :as illustrations]
    [gracie.routes.sketchbook-samples :as sketchbook-samples]
    [gracie.routes.comics :as comics]))

(def routes
  {"/" #'home/view
   "/illustrations/" #'illustrations/view
   "/sketchbook-samples/" #'sketchbook-samples/view
   "/comics/" #'comics/index-view
   "/comics/:slug/" #'comics/single-view})

