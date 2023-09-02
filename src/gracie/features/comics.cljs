(ns gracie.features.comics
 (:require
  [promesa.core :as p]
  [gracie.data-pipeline :refer [defhook]]
  [framework.assets :refer [fetch-image]]))

(defhook :comics :parse-project
 (fn comics-parse-project
  [original-project]
  {:id               (get original-project :id)
   :slug             (get original-project :slug)
   :title            (get original-project :title)
   :type             (get original-project :type)
   :featured         (= (get-in original-project [:properties :featured :checkbox]) true)
   :published        (= (get-in original-project [:properties :published :checkbox]) true)
   :image-url        (get-in original-project [:properties :image :files 0 :file :url])}))

(defhook :comics :queue-requests
 (fn comics-queue-requests
   [project]
   [{:id (:image-url project)
     :fetch #(fetch-image project "comics" (:image-url project))
     :reducer #(assoc %1 :image-url %2)}]))

(defhook :comics :format-project
 (fn comics-format-project
  [{:keys [project responses]}]
  (let [{:keys [image-url]} responses]
   (assoc project
          :image-url image-url
          :thumbnail image-url))))
