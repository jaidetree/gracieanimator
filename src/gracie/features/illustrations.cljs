(ns gracie.features.illustrations
 (:require
  [promesa.core :as p]
  [gracie.data-pipeline :refer [defhook]]
  [framework.assets :refer [fetch-image]]))


(defhook :illustrations :parse-project
 (fn illustrations-parse-project
  [original-project]
  {:id               (get original-project :id)
   :slug             (get original-project :slug)
   :title            (get original-project :title)
   :type             (get original-project :type)
   :featured         (= (get-in original-project [:properties :featured :checkbox]) true)
   :published        (= (get-in original-project [:properties :published :checkbox]) true)
   :image-url        (get-in original-project [:properties :image :files 0 :file :url])}))

(defhook :illustrations :queue-requests
 (fn illustrations-queue-requests
   [project]
   [{:id (:image-url project)
     :fetch #(fetch-image project
                          "illustrations"
                          (:image-url project))
     :reducer #(assoc %1 :image-url %2)}]))

(defhook :illustrations :format-project
 (fn illustrations-format-project
  [{:keys [project responses]}]
  (let [{:keys [image-url]} responses]
   (assoc project
          :image-url image-url
          :thumbnail image-url))))
