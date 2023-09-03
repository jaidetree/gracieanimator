(ns gracie.middleware
  (:require
   [clojure.pprint :refer [pprint]]
   [framework.utils :as u]
   [gracie.data-pipeline :as dp]
   [gracie.views.base :refer [base]]))

(defn wrap-data
  [handler]
  (fn [req]
    (handler (-> req
                 (assoc-in [:data :projects] (dp/all-projects))
                 (assoc-in [:data :pages] (dp/all-pages))))))

(defn wrap-dynamic-page-router
  [handler]
  (fn [req]
    (let [path-slug (u/slugify (:path req))
          pages (get-in req [:data :pages])
          page (->> pages
                    (some #(when (= (:slug %) path-slug) %)))]
      (if page
        {:headers (assoc (:headers req)
                         :Content-Type "text/html")
         :session (:session req)
         :status 200
         :body
         (base
           req (:data req)
           [:div
            [:h1.mb-8
             (:title page)]
            (into [:div] (:content page))])}
        (handler req)))))
