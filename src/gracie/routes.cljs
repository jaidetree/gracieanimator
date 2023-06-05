(ns gracie.routes
  (:require
    [gracie.routes.home :as home]))

(def routes
  {"/" home/view})

