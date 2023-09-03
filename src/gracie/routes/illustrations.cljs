(ns gracie.routes.illustrations
  (:require
    [framework.utils :as u]
    [clojure.pprint :refer [pprint]]
    [gracie.projects2 :as projects]))

(defn view
  [req {:keys [projects]}]
  (let [illustrations (->> projects
                           (filter #(projects/project-type? % :illustrations)))]
   {:status 200
    :session (:session req)
    :title "Illustrations"
    :view
    [:div [:h1.mb-8 "Illustrations"]
     [:div.illustrations.space-y-8
      (for [illustration illustrations]
        [:img
         {:key (:slug illustration)
          :src (:image-url illustration)
          :alt (:title illustration)}])]]}))
